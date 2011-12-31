from types import MethodType
from struct import pack, unpack, calcsize
from collections import namedtuple, defaultdict
import logging
import usb

_log = logging.getLogger("gat.ant_stream_device")

AntMessage = namedtuple("AntMessage", ["sync", "msg_id", "args"])

class AntStreamDevice(object):
    """
    An ANT hardware device with stream oriented communication.
    Composied of an AntMessageAssember which knows how to 
    covert to/form over-the-wire byte stream formats, and
    AntHardware which knows how to read/write to the device.
    """

    def __init__(self, ant_hardware, ant_message_assembler, ant_message_catalog=None):
        """
        Create a new instance of stream device, the given marshallers
        will be used to pack data send over wire. Catalog is used
        to dynamically generate methods which should be supported
        by this AntDevice. It is also used to optionally support
        keyword args.
        """
        self.hardware = ant_hardware
        self.assembler = ant_message_assembler
        self.listeners = defaultdict(list)
        self.enhance(ant_message_catalog)

    def enhance(self, catalog):
        """
        Enhance this instance with functions defined
        in the ant message catalog.
        """
        if catalog:
            for func in catalog.functions:
                def factory(msg_id):
                    def method(self, *args, **kwds):
                        self.exec_function(msg_id, *args, **kwds)
                    return method
                setattr(self, func.msg_name, MethodType(factory(func.msg_id), self, AntStreamDevice))
 
    def exec_function(self, msg_id, *args, **kwds):
        """
        Execute a function defined in this instance's
        message catalog.
        """
        msg = self.assembler.asm(msg_id, *args, **kwds)
        if _log.isEnabledFor(logging.DEBUG): _log.debug(">> " + str(self.assembler.disasm(msg)))
        self.hardware.write(msg)
        
#   def register_callback(self, msg_id, func):
#       """
#       Register a callback which should be invoked
#       when messages are received with the provided id.
#       """
#       self.unregister_callback(msgs_id, func)
#       self.listeners[msg_id].append(func)

#   def unregister_callback(self, msg_id, func):
#       """
#       Unregister the provided function.
#       """
#       self.listeners[msg_id].remove(func)

#   def poll(self):
#       """
#       Poll the input stream for messages from device,
#       and dispatch any events to registered listeners.
#       This method should typically be executed in
#       a spereate thread.
#       """
#       pass

#   def _read_msg(self, timeout=100, hard_timeout=1000):
#       """
#       Read a single message from this stream device.
#       Wait up to timeout ms for the start of a message.
#       Once the start of message is retreived, hard_timeout
#       is used, resting after each read of at least one byte,
#       until a complete message is retreived.
#       hard_timeout expiration raise error, and could leave
#       buffer in an irrecoverable state.
#       timeout, simple returns None.
#       """
#       pass


class AntMessageAssembler(object):
    """
    Provides a higher level view of message building
    than marshaller / unmaraller. adding support for
    AntMessageCatalog and named args where defined.
    """

    def __init__(self, ant_message_catalog, ant_message_marshaller):
        """
        Create an Assemblerr. The catalog and marshaller
        determin this instance's behaviours. Sepcificially which
        message types are supported, and which formats (legcacy
        or standart (WRT extended messages).
        """
        self.catalog = ant_message_catalog
        self.marshaller = ant_message_marshaller

    def asm(self, msg_id, *args, **kwds):
        """
        Return the string reperesnting the execion
        of function with give msg_id.
        """
        function = self.catalog.function_by_msg_id[msg_id]
        if kwds: args = function.msg_args(**kwds)
        return self.marshaller.marshall(function.msg_format, AntMessage(None, msg_id, args))

    def disasm(self, msg, lieniant=False):
        """
        Return an object description this message.
        If lieniant is false, errors could be raised
        while build messages, otherwise, some output
        is produced, even if format isn't specified.
        """
        msg_id = ord(msg[2])
        try:
            msg_type = self.catalog.entry_by_msg_id[msg_id]
            result = self.marshaller.unmarshall(msg_type.msg_format, msg, ignore_checksum=lieniant)
            args = msg_type.msg_args(*result.args) if msg_type.msg_args else result.args
            return AntMessage(result.sync, msg_id, args)
        except:
            if not lieniant: raise
            else: return AntMessage(ord(msg[0]), msg_id, [msg.encode("hex")])


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

    def unmarshall(self, pack_format, msg, ignore_checksum=False):
        """
        Convert the give message into an AntMessage tuple.
        """
        assert ignore_checksum or self.validate_checksum(msg)
        data = unpack("<BBB" + pack_format + "B", msg)
        return AntMessage(data[0], data[2], data[3:-1])


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

    def _read(self, n=1, timeout=100):
        """
        Read from the configure bulk endpoint.
        """
        return self.handle.bulkRead(self.end_in, n, timeout)

    def _write(self, buffer, timeout=100):
        """
        Write to the configured buld endpoint.
        """
        self.handle.bulkWrite(self.end_out, buffer, timeout)


# vim: et ts=4 sts=4 nowrap
