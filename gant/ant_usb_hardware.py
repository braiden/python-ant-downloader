import logging
import usb

_log = logging.getLogger("gant.ant_usb_hardware")

class UsbHardware(object):
    """
    Provide read/write access to a USB ANT stick via libUSB.
    e.g. nRF24AP2-USB. This class does not support usb devices
    that use an ftdi serial bringe. Use a SerialAntHardware them.
    """

    _dev = None

    def __init__(self, idVendor, idProduct, configuration=1, interface=0, altInterface=0, endpoint=0x01):
        """
        Create a new connection with USB device. idProduct, idVendor are required.
        Extended arguments allow for sellection of endpoints. This impelemnation
        only supports bulk transfers and no sort of message oriented approach.
        """
        for dev in self._find_usb_devices(idVendor, idProduct):
            # find the first usb device not already claimed
            try:
                self._handle = dev.open() 
                self._handle.setConfiguration(configuration)
                self._handle.claimInterface(interface)
                self._handle.setAltInterface(altInterface)
                self._end_out = endpoint
                self._end_in = endpoint | 0x80
                self._handle.clearHalt(self._end_out)
                self._handle.clearHalt(self._end_in)
                self._dev = dev
            except usb.USBError as e:
                if not [arg for arg in e.args if 'Device or resource busy' in arg]: raise
                else: _log.warn("Found device matching device, but already claimed. Will keep looking")
        if not self._dev:
            raise IOError("No avialible USB Device could be found with vid=0x%04x pid=0x%04x." % (idVendor, idProduct))

    def _find_usb_devices(self, idVendor, idProduct):
        """
        Search usb busess for the any device matching vid/pid.
        """
        for bus in usb.busses():
            for dev in bus.devices:
                if dev.idProduct == idProduct and dev.idVendor == idVendor:
                    yield dev

    def close(self):
        """
        Close and resources assocaited with this device.
        Read / write is no longer valid.
        """
        self._handle.releaseInterface()

    def read(self, n=4096, timeout=100):
        """
        Read from the usb device's configured bulk endpoint
        """
        data = None
        try:
            data = self._handle.bulkRead(self._end_in, n, timeout)
        except usb.USBError as e:
            if e.args != ('No error',): raise e # http://bugs.debian.org/476796
            # The bug is acutally far worse that whats documented on debian site.
            # Since python usb is calling usb_strerror even on success, it will
            # errouneously pickup an errno from other device than this one.
            # this make very hard (impossible) to open more than one usb device at time.
            # FIXME upgrade to libusb1? but, want stick with moduels that ship with deb
        if data:
            return reduce(lambda x, y: x + y, map(lambda c: chr(c), data))
        else:
            return ""

    def write(self, buffer, timeout=100):
        """
        Write to the configured bulk endpoint.
        """
        try:
            self._handle.bulkWrite(self._end_out, buffer, timeout)
        except usb.USBError as e:
            if e.args != ('No error',): raise e # http://bugs.debian.org/476796


# vim: et ts=4 sts=4
