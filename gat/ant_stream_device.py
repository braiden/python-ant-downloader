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

    def __init__(self, ant_hardware, ant_message_marshaller, ant_function_catalog, ant_callback_catalog):
        """
        Create a new instance of stream device, the given marshallers
        will be used to pack data send over wire. Catalog is used
        to dynamically generate methods which should be supported
        by this AntDevice. It is also used to optionally support
        keyword args.
        """
        self._hardware = ant_hardware
        self._marshaller = ant_message_marshaller
        self._functions = ant_function_catalog
        self._callbacks = ant_callback_catalog
        self._enhance()

    def _enhance(self):
        """
        Enhance this instance with functions defined
        in the ant message catalog.
        """
        for func in self._functions.entries:
            def factory(msg_id):
                def method(self, *args, **kwds):
                    self.exec_function(msg_id, *args, **kwds)
                return method
            setattr(self, func.msg_name, MethodType(factory(func.msg_id), self, AntStreamDevice))
 
    def _asm(self, catalog, msg_id, args, kwds):
        """
        Return the string reperesnting the execution
        of function with give msg_id.
        """
        function = catalog.entry_by_msg_id[msg_id]
        if kwds: args = function.msg_args(**kwds)
        return self._marshaller.marshall(function.msg_format, msg_id, args)

    def _disasm(self, catalog, msg):
        """
        Return an object description this message.
        If lieniant is false, errors could be raised
        while build messages, otherwise, some output
        is produced, even if format isn't specified.
        """
        msg_id = self._marshaller.extract_msg_id(msg)
        msg_type = catalog.entry_by_msg_id[msg_id]
        (sync, msgs_id, args, extended_attrs) = self._marshaller.unmarshall(msg_type.msg_format, msg)
        args = msg_type.msg_args(*args) if msg_type.msg_args else args
        return AntMessage(sync, msg_id, args, extended_attrs)

    def exec_function(self, msg_id, *args, **kwds):
        """
        Execute a function defined in this instance's
        message catalog.
        """
        msg = self._asm(self._functions, msg_id, args, kwds)
        if _log.isEnabledFor(logging.DEBUG):
            _log.debug("<< " + str(self.disasm_output_msg(msg)))
        self._hardware.write(msg)

    def disasm_output_msg(self, msg):
        """
        Convert the string msg encoded for output to
        an object representation suitbale for debug.
        """
        return self._disasm(self._functions, msg)
        
    def disasm_input_msg(self, msg):
        """
        Convert the string msg encoded from input to
        an object representation suitbale for debug.
        """
        return self._disasm(self._callbacks, msg)

    def _read(self, timeout=100):
        """
        Read one complete mesage frame from a device.
        Timeout is reset after each successful read
        of at least one byte. Value of timeout must be
        sufficiently large to guarentee that the ant
        device has had sufficient time to commit message.
        Should read timeout after partially reading a
        message, the stream will be left in irrecoverable
        state, and most likely device will need reset.
        """
        msg = ""
        remaining_length = self._marshaller.header_length

        while remaining_length:
            msg_segment = self._hardware.read(n=remaining_length, timeout=timeout)
            remaining_length -= len(msg_segment)
            msg += msg_segment
            if not msg_segment:
                break
            elif len(msg) == self._marshaller.header_length:
                remaining_length = self._marshaller.extract_msg_length(msg) - len(msg)

        # fail on a partial read
        assert not (msg and remaining_length) 
        return msg


class AntMessageMarshaller(object):
    """
    This class provides the basic implementation for packing
    and unpacking messages for serial communication with device.
    This implemenation has NO support for extended message.
    Enabling them while using this implemation will fail.
    All operations specific to what a message looks like
    in transit should be implemented here. (so implemenation
    can be replaced to support additional devices)
    """
    
    header_length = 3
    footer_length = 1

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

    def extract_msg_id(self, msg):
        """
        Return the msg_id of the message
        in provided string.
        """
        return ord(msg[2])

    def extract_msg_length(self, msg):
        """
        Return the total length of the message.
        This is not the legth of data bytes, but
        the total legth including header and checksum.
        """
        return ord(msg[1]) + self.header_length + self.footer_length

    def marshall(self, pack_format, msg_id, args):
        """
        Convert the give data into a serialized message. 
        """
        length = self._calcsize(pack_format)
        data = pack("<BBB" + pack_format, 0xA4, length, msg_id, *args)
        return data + pack("<B", self.generate_checksum(data))

    def unmarshall(self, pack_format, msg, ignore_checksum=False):
        """
        Convert the give message into tuple.
        [0] = sync, [1] = msg_id, [2] = args[], [3] = extendedArgs
        """
        assert ignore_checksum or self.validate_checksum(msg)
        data = unpack("<BBB" + pack_format + "B", msg)
        return (data[0], data[2], data[3:-1], None)

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
        # checksum was validated above if required, don't allow
        # super to check it, it will be wrong since extended data is stripped
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
