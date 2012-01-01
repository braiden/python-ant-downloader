import logging
import usb

_log = logging.getLogger("gat.ant_usb_device")

class UsbAntHardware(object):
    """
    Provide read/write access to a USB ANT stick via libUSB.
    e.g. nRF24AP2-USB. This class does not support usb devices
    that use an ftdi serial bringe. Use a SerialAntHardware them.
    """
    
    def __init__(self, idVendor, idProduct, configuration=0, interface=0, altInterface=0, endpoint=0x01):
        """
        Create a new connection with USB device. idProduct, idVendor are required.
        Extended arguments allow for sellection of endpoints. This impelemnation
        only supports bulk transfers and no sort of message oriented approach.
        """
        self.dev = self.find_usb_device(idVendor, idProduct)
        if not self.dev:
            raise IOError("No USB Device could be found with vid=0x%04x pid=0x%04x." % (idVendor, idProduct))
        self.handle = self.dev.open() 
        self.cfg = self.dev.configurations[configuration]
        self.handle.setConfiguration(self.cfg)
        self.interface = self.cfg.interfaces[interface][altInterface]
        self.handle.setAltInterface(self.interface)
        self.handle.claimInterface(self.interface)
        self.end_out = endpoint
        self.end_in = endpoint & 0x80

    def find_usb_device(self, idVendor, idProduct):
        """
        Search usb busess for the first device matching vid/pid.
        """
        for bus in usb.busses():
            for dev in bus.devices:
                if dev.idProduct == idProduct and dev.idVendor == idVendor:
                    return dev

    def read(self, n=1, timeout=100):
        """
        Read from the configure bulk endpoint.
        """
        return self.handle.bulkRead(self.end_in, n, timeout)

    def write(self, buffer, timeout=100):
        """
        Write to the configured buld endpoint.
        """
        self.handle.bulkWrite(self.end_out, buffer, timeout)


# vim: et ts=4 sts=4 nowrap
