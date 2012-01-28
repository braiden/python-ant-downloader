import usb.core
import usb.util
import errno
import logging

_LOG = logging.getLogger("antagent.usb")

class UsbHardware(object):
	
	def __init__(self, id_vendor=0x0fcf, id_product=0x1008, ep=1):
		for dev in usb.core.find(idVendor=id_vendor, idProduct=id_product, find_all=True):
			try:
				dev.set_configuration()
				usb.util.claim_interface(dev, 0)
				self.dev = dev
				self.ep = ep
				break
			except IOError as (err, msg):
				if err == errno.EBUSY:
					_LOG.info("Found device with matching vid(0x%04x) pid(0x%04x), but interface already claimed.", id_vendor, id_product)
				else:
					raise
		else:
			raise IOError(errno.ENOENT, "No availbile device matching vid(0x%04x) pid(0x%04x)." % (id_vendor, id_product))

	def close(self):
		usb.util.release_interface(self.dev, 0)

	def write(self, data, timeout):
		transfered = self.dev.write(self.ep | usb.util.ENDPOINT_OUT, data, timeout=timeout)
		if transfered != len(data):
			raise IOError(errno.EOVERFLOW, "Write too large, len(data) > wMaxPacketSize not supported.)

	def read(self, timeout):
		return self.dev.read(self.ep | usb.util.ENDPOINT_IN, 16384, timeout=timeout)
