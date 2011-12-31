from types import MethodType
from struct import pack, unpack, calcsize
from collections import namedtuple
import usb

AntMessage = namedtuple("AntMessage", ["sync", "msg_id", "args"])


class AntStreamDeviceBase(object):
    """
    An ANT hardware device with stream oriented communication.
    Implementors should extend this class, and implement real
    read()/write() methods. This class exposes every method
    defined in "ANT Message Protcol and Usage". The methods are
    dynamically generated from the function definitions declared
    in metadata.
    """

    def __init__(self, ant_message_catalog, ant_message_marshaller, ant_message_unmarshaller=None):
        """
        Create a new instance of stream device, the given marshallers
        will be used to pack data send over wire. Catalog is used
        to dynamically generate methods which should be supported
        by this AntDevice. It is also used to optionally support
        keyword args.
        """
        self.catalog = ant_message_catalog
        self.marshaller = ant_message_marshaller
        self.unmarshaller = ant_message_unmarshaller or ant_message_marshaller
        self.enhance()

    def enhance(self):
        """
        Enhance this instance with functions defined
        in the ant message catalog.
        """
        for func in self.catalog.functions:
            def factory(msg_id):
                def method(self, *args, **kwds):
                    self.exec_function(msg_id, *args, **kwds)
                return method
            setattr(self, func.msg_name, MethodType(factory(func.msg_id), self, AntStreamDeviceBase))

    def exec_function(self, msg_id, *args, **kwds):
        """
        Execute a function defined in this instance's
        message catalog.
        """
        function = self.catalog.functionByMsgId[msg_id]
        if kwds: args = function.msg_args(**kwds)
        msg = self.marshaller.marshall(function.msg_format, AntMessage(None, msg_id, args))
        self.write(msg)
        

class AntMessageMarshaller(object):
    """
    This class provides the basic implementation for packing
    and unpacking messages for serial communication with device.
    This implemenation has NO support for extended message.
    Enabling them while using this implemation will fail.
    """
    
    def generate_checksum(self, msg):
        """
        Generate the checksum for provided msg. (xor of all bytes)
        """
        return reduce(lambda x, y: x ^ y, map(lambda x: ord(x), msg))

    def validate_checksum(self, msg):
        """
        Validate the checksum of provided message.
        """
        return ord(msg[-1]) == self.generate_checksum(msg[:-1])

    def marshall(self, pack_format, msg):
        """
        Convert the give msg into a stream represetnation.
        """
        sync = msg.sync or 0xA4
        length = calcsize("<" + pack_format)
        data = pack("<BBB" + pack_format, sync, length, msg.msg_id, *msg.args)
        return data + pack("<B", self.generate_checksum(data))

    def unmarshall(self, pack_format, msg):
        """
        Convert the give message into an AntMessage tuple.
        """
        assert self.validate_checksum(msg)
        data = unpack("<BBB" + pack_format + "B", msg)
        return AntMessage(data[0], data[2], data[3:-1])


class UsbAntStreamDevice(AntStreamDeviceBase):
    """
    An implementation of AntStreamDevice which uses libusb.
    """
    
    def __init__(self, idVendor, idProduct, configuration=0, interface=0, altInterface=0, endpointOut=0x01, endpointIn=0x81):
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
        self.end_out = endpointOut 
        self.end_in = endpointIn

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
