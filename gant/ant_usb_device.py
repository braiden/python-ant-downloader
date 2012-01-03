import logging
import usb
from ant_stream_device import AntStreamDevice

_log = logging.getLogger("gat.ant_usb_device")


class AntUsbDevice(AntStreamDevice):
    
    def _read(self, timeout=100):
        """
        Read one block (message) from usb device.
        """
        return self._hardware.read(timeout=timeout)


class AntUsbHardware(object):
    """
    Provide read/write access to a USB ANT stick via libUSB.
    e.g. nRF24AP2-USB. This class does not support usb devices
    that use an ftdi serial bringe. Use a SerialAntHardware them.
    """
    
    def __init__(self, idVendor, idProduct, configuration=1, interface=0, altInterface=0, endpoint=0x01):
        """
        Create a new connection with USB device. idProduct, idVendor are required.
        Extended arguments allow for sellection of endpoints. This impelemnation
        only supports bulk transfers and no sort of message oriented approach.
        """
        self._dev = self._find_usb_device(idVendor, idProduct)
        if not self._dev:
            raise IOError("No USB Device could be found with vid=0x%04x pid=0x%04x." % (idVendor, idProduct))
        self._handle = self._dev.open() 
        self._handle.setConfiguration(configuration)
        self._handle.claimInterface(interface)
        self._handle.setAltInterface(altInterface)
        self._end_out = endpoint
        self._end_in = endpoint | 0x80
        self._handle.clearHalt(self._end_out)
        self._handle.clearHalt(self._end_in)

    def _find_usb_device(self, idVendor, idProduct):
        """
        Search usb busess for the first device matching vid/pid.
        """
        for bus in usb.busses():
            for dev in bus.devices:
                if dev.idProduct == idProduct and dev.idVendor == idVendor:
                    return dev

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


# vim: et ts=4 sts=4 nowrap
