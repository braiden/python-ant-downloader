from types import MethodType
from struct import pack, unpack, calcsize
from collections import namedtuple, defaultdict
import logging

_log = logging.getLogger("gat.ant_stream_device")

AntMessage = namedtuple("AntMessage", ["sync", "msg_id", "args", "extendedArgs"])

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
        return self.marshaller.marshall(function.msg_format, AntMessage(None, msg_id, args, None))

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
            return AntMessage(result.sync, msg_id, args, None)
        except:
            if not lieniant: raise
            else: return AntMessage(ord(msg[0]), msg_id, msg[3:-1], None)


class AntMessageMarshaller(object):
    """
    This class provides the basic implementation for packing
    and unpacking messages for serial communication with device.
    This implemenation has NO support for extended message.
    Enabling them while using this implemation will fail.
    """
    
    def _calcsize(self, pack_format):
        """
        Return the size in bytes used by provided format.
        Make sure to qualfiy with "<" for packed (non-padded)
        little endian.
        """
        return calcsize("<" + pack_format)

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
        length = self._calcsize(pack_format)
        data = pack("<BBB" + pack_format, sync, length, msg.msg_id, *msg.args)
        return data + pack("<B", self.generate_checksum(data))

    def unmarshall(self, pack_format, msg, ignore_checksum=False):
        """
        Convert the give message into an AntMessage tuple.
        """
        assert ignore_checksum or self.validate_checksum(msg)
        data = unpack("<BBB" + pack_format + "B", msg)
        return AntMessage(data[0], data[2], data[3:-1], None)


class AntExtendedMessageMarshaller(AntMessageMarshaller):
    """
    A message marshaller adding support for
    unmarshalling of standard (not legacy) extended data.
    """

    def _extract_extended_data(self, pack_format, msg):
        """
        Return the extended data associated with current
        message starting with the flag byte. returns []
        if the message contains no extended data.
        """
        arg_size = self._calcsize(pack_format)
        return msg[3 + arg_size:-1]

    def _remove_extended_data(self, pack_format, msg):
        """
        Return the message with extended data removed.
        The length byte remains unchanged (even if data
        was removed.) if msg is not extended form, no
        changes are applied.
        """
        arg_size = self._calcsize(pack_format)
        return msg[0:3 + arg_size] + msg[-1:]

    def unmarshall(self, pack_format, msg, ignore_checksum=False):
        """
        Covert the emssage into AntMessage including extended data
        if any was provided in the message.
        """
        assert ignore_checksum or self.validate_checksum(msg)
        result = super(AntExtendedMessageMarshaller, self).unmarshall(
                pack_format, self._remove_extended_data(pack_format, msg), ignore_checksum=True)
        return result


class AntLegacyExtendedMessageMarshaller(AntExtendedMessageMarshaller):
    """
    ExtendedMessageMarshaller supporting legacy format
    (where the extended data imediately follows the msg_id)
    """

    def _extract_extended_data(self, pack_format, msg):
        arg_size = calcsize("<" + pack_format)
        return msg[3:-1 - arg_size]

    def _remove_extended_data(self, pack_format, msg):
        arg_size = calcsize("<" + pack_format)
        return msg[0:3] + msg[-1 - arg_size:]


# vim: et ts=4 sts=4 nowrap
