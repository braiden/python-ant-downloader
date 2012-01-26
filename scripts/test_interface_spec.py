#!/usr/bin/python

import sys
import time
import threading
import logging
import collections
import struct

import gant.ant_usb_hardware as hw
import gant.ant_core as core

logging.basicConfig(level=logging.DEBUG, out=sys.stderr, format="%(asctime)s %(levelname)s %(message)s")
LOG = logging.getLogger()

AntMessage = collections.namedtuple("AntMessage", ["msg_id", "msg_args"])

def is_ant_ack(msg, msg_id):
	if msg_id == core.MessageType.RESET_SYSTEM:
		return msg.msg_id == core.MessageType.STARTUP_MESSAGE
	else:
		return (msg.msg_id == core.MessageType.CHANNEL_RESPONSE_OR_EVENT
			and msg.msg_args[1] == msg_id and not msg.msg_args[2])


class State(object):

	def __init__(self, dispatcher):
		self.dispatcher = dispatcher

	def send(self, msg_id, *args):
		self.dispatcher.send(msg_id, *args)

	def channel_event(self, msg):
		msg_id_name = core.value_of(core.MessageType, msg.msg_id)
		LOG.debug("Channel Event. msg_id=%s, msg_args=%s", msg_id_name, msg.msg_args)

	def radio_event(self, msg):
		channel_number, msg_id, msg_code = msg.msg_args
		msg_code_name = core.value_of(core.RadioEventType, msg_code)
		LOG.debug("Rf Event. channel=%s, msg_code_name=%s", channel_number, msg_code_name)


class OpenChannelState(State):

	current_command = None
	state = 0

	def __init__(self, dispatcher):
		super(OpenChannelState, self).__init__(dispatcher)
		self.channel_event(None)

	def send(self, msg_id, *args):
		self.current_command = msg_id
		self.dispatcher.send(msg_id, *args)

	def channel_event(self, msg):
		if self.current_command and is_ant_ack(msg, self.current_command):
			LOG.debug("Channel Event. ACK msg_id_name=%s", core.value_of(core.MessageType, self.current_command))
			self.current_command = None
			self.state += 1

		if not self.current_command:
			if self.state == 0:
				self.send(core.MessageType.RESET_SYSTEM)
			elif self.state == 1:
				self.send(core.MessageType.NETWORK_KEY, 0, "\xa8\xa4\x23\xb9\xf5\x5e\x63\xc1")
			elif self.state == 2:
				self.send(core.MessageType.ASSIGN_CHANNEL, 0, 0, 0)
			elif self.state == 3:
				self.send(core.MessageType.CHANNEL_ID, 0, 0, 0, 0)
			elif self.state == 4:
				self.send(core.MessageType.CHANNEL_PERIOD, 0, 0x1000)
			elif self.state == 5:
				self.send(core.MessageType.CHANNEL_SEARCH_TIMEOUT, 0, 0xFF)
			elif self.state == 6:
				self.send(core.MessageType.CHANNEL_RF_FREQ, 0, 50)
			elif self.state == 7:
				self.send(core.MessageType.SEARCH_WAVEFORM, 0, 0x0053)
			elif self.state == 8:
				self.send(core.MessageType.OPEN_CHANNEL, 0)
			elif self.state == 9:
				return AntFsState(self.dispatcher)


class AntFsState(State):

		def __init__(self, dispatcher):
			super(AntFsState, self).__init__(dispatcher)
			self.state = State(None)
			self.last_beacon = None

		def _create_state(self, client_status):
			if client_status == 0:
				return AntFsLink(dispatcher)
			elif client_status == 1:
				return AntFsAuth(dispatcher)
			else:
				return State(dispatcher)

		def channel_event(self, msg):
			if msg.msg_id == core.MessageType.BROADCAST_DATA and ord(msg.msg_args[1][0]) == 0x43:
				beacon_id, status_1, status_2, auth_type, sn = struct.unpack("<BBBBI", msg.msg_args[1])
				if status_2 != 3 and self.last_beacon != status_2:
					LOG.debug("ANTFS Beacon State Changed, Transitioning to new state. client_status=%d", status_2)
					self.last_beacon = status_2
					self.state.channel_event(msg)
					self.state = self._create_state(status_2)
			return self.state.channel_event(msg)

		def radio_event(self, msg):
			return self.state.radio_event(msg)

class AntFsLink(State):

	def __init__(self, dispatcher):
		super(AntFsLink, self).__init__(dispatcher)
		self.send(core.MessageType.ACKNOWLEDGED_DATA, 0, "\x44\x02\x32\x04\xca\x00\x00\x00")

	def radio_event(self, msg):
		if msg.msg_id == core.MessageType.CHANNEL_RESPONSE_OR_EVENT \
				and msg.msg_args[1] == 1 and msg.msg_args[2] == core.RadioEventType.TRANSFER_TX_FAILED:
			LOG.debug("Failed to send LINK, will try again.")
			self.send(core.MessageType.ACKNOWLEDGED_DATA, 0, "\x44\x02\x32\x04\xca\x00\x00\x00")


class AntFsAuth(State):

	def __init__(self, dispatcher):
		super(AntFsAuth, self).__init__(dispatcher)
		self.burst_data = ""
		self.busy = False
		self.client_sn = None
		self.pairing_key = None

	def channel_event(self, msg):
		data = None
		if msg.msg_id == core.MessageType.BURST_TRANSFER_PACKET:
			self.burst_data += msg.msg_args[1]
		elif msg.msg_id == core.MessageType.ACKNOWLEDGED_DATA:
			data = msg.msg_args[1]
		elif msg.msg_id == core.MessageType.BROADCAST_DATA and self.burst_data:
			data = self.burst_data[16:]
			self.burst_data = ""

		if data and not self.client_sn:
			LOG.debug("Client SN: %s", data.encode("hex"))
			self.client_sn = data
			self.busy = False
		elif data and not self.pairing_key:
			LOG.debug("Client Key: %s", data.encode("hex"))
			self.pairing_key = data
			self.busy = False

		if not self.busy and not self.client_sn:
			LOG.debug("Requesting client SN#")
			self.send(core.MessageType.ACKNOWLEDGED_DATA, 0, "\x44\x04\x01\x00\xca\x00\x00\x00")
			self.busy = True
		elif not self.busy and not self.pairing_key:
			LOG.debug("Requesting pairing with Client")
			self.send(core.MessageType.ACKNOWLEDGED_DATA, 0, "\x44\x04\x02\x00\xca\x00\x00\x00")
			self.busy = True


	def radio_event(self, msg):
		if msg.msg_id == core.MessageType.CHANNEL_RESPONSE_OR_EVENT \
				and msg.msg_args[1] == 1 and msg.msg_args[2] == core.RadioEventType.TRANSFER_RX_FAILED:
			LOG.debug("Burst failed, will retry.")
			self.burst_data = ""
			self.busy = False


class EventLoop(threading.Thread, core.Listener):

	def __init__(self, dispatcher):
		super(EventLoop, self).__init__()
		self.dispatcher = dispatcher
		self.state = OpenChannelState(dispatcher)

	def run(self):
		try:
			self.dispatcher.loop(self)
		finally:
			try: self.dispatcher.send(core.MessageType.RESET_SYSTEM)
			except: LOG.warning("Failed to reset system on exit.", exc_info=True)

	def on_message(self, dispatcher, msg):
		msg = AntMessage(*msg)
		if msg.msg_id == core.MessageType.CHANNEL_RESPONSE_OR_EVENT and msg.msg_args[1] == 1:
			state = self.state.radio_event(msg)
		else:
			state = self.state.channel_event(msg)
		if state:
			LOG.debug("Transition %s => %s.", self.state.__class__.__name__, state.__class__.__name__)
			self.state = state
			return True
		else:
			return False if state is None else None


try:
	dev = hw.UsbHardware(id_vendor=0x0fcf, id_product=0x1008)
	dispatcher = core.Dispatcher(dev, core.Marshaller())
	t = EventLoop(dispatcher)
	t.run()
finally:
	try: dev.close()
	except: LOG.warning("Failed to close hardware device.", exc_info=True)
