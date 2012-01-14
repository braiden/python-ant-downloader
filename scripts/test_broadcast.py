#!/usr/bin/python

import gant
import logging
import sys
import time

logging.basicConfig(level=logging.DEBUG, out=sys.stderr, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger()

class MasterDevice(gant.ChannelListener):

	def __init__(self, dev):
		self._dev = dev

	def open(self):
		net = self._dev.networks[0]
		chan = self._dev.channels[0]
		chan.network = net
		chan.channel_type = 0x10
		chan.channel_listener = self
		chan.open()

	def channel_openned(self, async):
		log.debug("MASTER: channel open")
		async.send_broadcast_data("\x00" * 8)

	def broadcast_data_received(self, async, data):
		log.debug("MASTER: broadcast recieved")
		async.send_broadcast_data(data)


class SlaveDevice(gant.ChannelListener):
	
	busy = False
	n = 0

	def __init__(self, dev):
		self._dev = dev

	def open(self):
		net = self._dev.networks[0]
		chan = self._dev.channels[0]
		chan.network = net
		chan.channel_type = 0x00
		chan.channel_listener = self
		chan.open()

	def broadcast_data_received(self, async, data):
		log.debug("SLAVE: broadcast recieved")
		if not self.busy:
			self.n = max(self.n, ord(data[0]) + 1)
			async.send_broadcast_data(chr(self.n) * 8)
			self.busy = True

	def broadcast_data_sent(self, async):
		log.debug("SLAVE: reply complete")
		self.busy = False


master = MasterDevice(gant.GarminAntDevice())
master.open()

slave = SlaveDevice(gant.GarminAntDevice())
slave.open()

time.sleep(60)

# vim et ts=4 sts=8
