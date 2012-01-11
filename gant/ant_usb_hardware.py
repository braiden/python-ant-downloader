import logging
import array
from gant.lib.libusb10 import get_backend, USBError

_log = logging.getLogger("gant.ant_usb_hardware")
_backend = get_backend()

def find_usb_devices(id_product, id_vendor):
    """
    Generator of a list containing all devives
    matching idVendor and idProduct.
    """
    for dev in _backend.enumerate_devices():
        descriptor = _backend.get_device_descriptor(dev)
        if descriptor.idProduct == id_product and descriptor.idVendor == id_vendor:
            yield dev


class UsbHardware(object):
    """
    Provide read/write access to a USB ANT stick via libUSB.
    e.g. nRF24AP2-USB. This class does not support usb devices
    that use an ftdi serial bringe. Use a SerialAntHardware them.
    """

    _handle = None

    def __init__(self, id_product, id_vendor, configuration=1, interface=0, alt_interface=0, endpoint=0x01):
        """
        Create a new connection with USB device. idProduct, idVendor are required.
        Extended arguments allow for sellection of endpoints. This impelemnation
        only supports bulk transfers and no sort of message oriented approach.
        """
        for dev in find_usb_devices(id_product, id_vendor):
            # not sure how to check if the device is claimed already.
            # so, just keep trying each matching device until on succeeds
            try:
                self._handle = _backend.open_device(dev)
                _backend.set_configuration(self._handle, configuration)
                _backend.claim_interface(self._handle, interface)
                _backend.set_interface_altsetting(self._handle, interface, alt_interface)
                self._intf = interface
                self._ep = endpoint
                break
            except USBError as e:
                (errno, errstring) = e.args
                _backend.close_device(self._handle)
                self._handle = None
                if errno == 16: # device busy
                    _log.warn("Found device with idVendor=%d, idProduct=%d, but resource is busy." % (id_vendor, id_product))
                else:
                    _log.warn("Failed to open device, will try again if any other matching devices exist.", exc_info=True)
        if not self._handle:
            raise IOError("No avialible USB Device could be found with vid=0x%04x pid=0x%04x." % (id_vendor, id_product))

    def close(self):
        """
        Close and resources assocaited with this device.
        Read / write is no longer valid.
        """
        if self._handle:
            _backend.release_interface(self._handle, self._intf)
            _backend.close_device(self._handle)
            self._handle = None

    def read(self, size=4096, timeout=100):
        """
        Read from the usb device's configured bulk endpoint
        """
        data = ""
        try:
            data = _backend.bulk_read(self._handle, self._ep | 0x80, self._intf, size, timeout)
            data = data.tostring() if data else ""
        except USBError as e:
            (errno, errstring) = e.args
            if errno != 110: # read timeout
                raise
        return data

    def write(self, data, timeout=100):
        """
        Write to the configured bulk endpoint.
        """
        arr = array.array("b", data)
        _backend.bulk_write(self._handle, self._ep, self._intf, arr, timeout)


# vim: et ts=4 sts=4
