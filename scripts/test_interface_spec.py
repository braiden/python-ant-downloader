#!/usr/bin/python

import sys
import time
import threading
import logging
import collections

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
		LOG.debug("Channel Event. msg_id=%d, msg_args=%s", msg_id_name, msg.msg_args)
		return True

	def radio_event(self, msg):
		channel_number, msg_id, msg_code = msg.msg_args
		msg_code_name = core.value_of(core.RadioEventType, msg_code)
		LOG.debug("Rf Event. channel=%d, msg_code_name=%s", channel_number, msg_code_name)
		return True


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
				self.send(core.MessageType.OPEN_CHANNEL, 0)

		return True


class EventLoop(threading.Thread, core.Listener):

	def __init__(self, dispatcher):
		super(EventLoop, self).__init__()
		self.dispatcher = dispatcher
		self.state = OpenChannelState(dispatcher)

	def run(self):
		try:
			self.dispatcher.loop(self)
		finally:
			try: self.send(core.MessageType.RESET_SYSTEM)
			except: LOG.warning("Failed to reset system on exit.", exc_info=True)

	def on_message(self, dispatcher, msg):
		msg = AntMessage(*msg)
		if msg.msg_id == core.MessageType.CHANNEL_RESPONSE_OR_EVENT:
			channel_number, msg_id, msg_code = msg.msg_args
			if msg_id == 1:
				return self.state.radio_event(msg)
		return self.state.channel_event(msg)


try:
	dev = hw.UsbHardware(id_vendor=0x0fcf, id_product=0x1008)
	dispatcher = core.Dispatcher(dev, core.Marshaller())
	t = EventLoop(dispatcher)
	t.run()
except KeyboardInterrupt:
	LOG.debug("KeyboardInterrupt")
	dev.close()
finally:
	try: dev.close()
	except: LOG.warning("Failed to close hardware device.", exc_info=True)
