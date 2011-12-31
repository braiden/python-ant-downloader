from struct import pack, unpack, calcsize
from collections import namedtuple
from ganttools.antdevice import AntUsbDevice

AntFunctionTableEntry = namedtuple("FunctionTableEntry", ["sync", "msg_id", "msg_format", "arg_names"])
AntExtendedData = namedtuple("AntExtendedData", ["deviceNumber", "deviceType", "transType", "measurementType", "rssiValue", "thresholdConfigValue", "rxTimestamp"]);
AntMessage = namedtuple("AntMessage", ["sync", "msg_length", "msg_id", "args", "extended_data", "checksum"]);

class AntModule(object):
    """
    High-level ANT API. Main entry for
    client applications. Should abstract
    most of the differences between different
    controller chips and connection types.
    """

    def __init__(self, controller, device):
        pass


class AntUsb2(AntModule):
    """
    An ant module assuming AntUSB2.
    nRF24AP2 connect to USB
    """

    def __init__(self, idVendor=0x0fcf, idProduct=0x1008):
        device = AntUsbDevice(idVendor, idProduct) 
        super().__init__(None, device)


class AntFunction(object):
    """
    An instance of AntFunction encapsulates an
    ANT message function defined in section 9.3
    of protocol specification. It provides methods
    for assembling and disassembline binary data.
    """

    def __init__(self, sync, msg_id, msg_format, arg_names=None):
        """
        Create a new AntFunction with the given MSG ID.
        msg_format is the python struct.pack format string matching
        the arguments defined in ant specification.
        arg_names can provide a namedtuple which describse
        this function and its arguments. This is optional, and
        is mainly intended to for pretty-printing trace data
        captures from windows driver. But, providing a named
        tuple also allows for keyword args instead of positional.
        """
        self.sync = sync
        self.msg_id = msg_id
        self.msg_format = msg_format
        self.msg_length = calcsize("<" + self.msg_format)
        self.arg_names = arg_names
        
    def checksum(self, msg):
        """
        Generate a checksum of the given input.
        Per spec xor of all data including sync.
        """
        return reduce(lambda x, y: x ^ y, map(lambda x: ord(x), msg))

    def verify_checksum(self, msg):
        """
        Return true if checksum is valid for the given message.
        """
        return ord(msg[-1]) == self.checksum(msg[:-1])

    def pack(self, *args, **kwds):
        """
        Return a byte array which represents the data
        needing to be written to device to execute
        operation with the provided arguments.
        """
        if kwds and self.arg_names:
            args = self.arg_names(**kwds)
        data = pack("<3B" + self.msg_format, self.sync, self.msg_length, self.msg_id, *args)
        return data + pack("B", self.checksum(data))

    def remove_extended_data_bytes(self, msg):
        """
        Return a message including only data bytes.
        Any extended data if existed, is removed.
        This method supports standard format,
        not legacy. see section 7.1.1.
        """
        return msg[:3+self.msg_length] + msg[-1:]

    def get_extended_data_bytes(self, msg):
        """
        Return extended data contained within
        the provided message. returns []
        if no extended data is availible,
        otherwise, string starting with the
        flag byte. standard format
        """
        return msg[3+self.msg_length:-1]

    def unpack(self, msg):
        """
        Unpack the give message to its arguments.
        Extended data, if it exists is ignored.
        """
        return unpack("<BBB" + self.msg_format + "B", self.remove_extended_data_bytes(msg))

    def is_supported(self, msg):
        """
        Return true if the provided string is a serialized
        representation of this function's output
        """
        return len(msg) > 4 and ord(msg[0]) == self.sync and ord(msg[2]) == self.msg_id

    def is_extended(self, msg):
        """
        Return true if the given message contains any extended data.
        """
        return self.is_supported(msg) and ord(msg[1]) > self.msg_length 

    def get_args(self, msg):
        """
        Return the args which were passed as part of this
        message. If a namedtuple was provided, the returned
        object will also have args availible by name.
        """
        if self.is_supported(msg):
            tokens = self.unpack(msg)
            arg_names = self.arg_names or self.create_default_arg_names(len(tokens) - 4)
            cmd = arg_names(*tokens[3:-1])
            return cmd

    def disasm(self, msg):
        """
        Return a tuple descriping the provided message
        and its arguments. Will return None if the message
        is not known by this function.
        [0] = sync byte
        [1] = msg length
        [2] = msg id
        [3] = arguments as tuple
        [4] = extended arguments
        [5] = actual checksum
        """
        if self.is_supported(msg):
            tokens = self.unpack(msg)
            sync = tokens[0]
            length = tokens[1]
            msg_id = tokens[2];
            args = self.get_args(msg)
            msg_checksum = tokens[-1]
            return AntMessage(sync, length, msg_id, args, None, msg_checksum)

    def create_default_arg_names(self, size):
        return namedtuple("ANT_0x%x" % self.msg_id, map(lambda n: "arg%d" % n, range(0, size)))

    def __call__(self, device, *args, **kwds):
        """
        Execute this command on the given target device.
        """
        data = self.pack(*args, **kwds)
        device.write(data)


class AntFunctionTable(object):
    """
    An AntFunctionTable represents a collection
    AntFunctions which are bound to a specific
    peice of hardware. Methods are exposed as
    properties of this object, and can be called
    to interact with hardware. This class could
    support all AntFunction or expose only a
    subset which are supported by the target
    device. The acuall implementation of functions
    determines if this device acts in standard
    or legacy mode where applicable.
    """

    def __init__(self, ant_device, ant_functions):
        self.ant_device = ant_device
        self.ant_functions = ant_functions

    def __getattr__(self, name):
        func = self.ant_functions[name]
        return lambda *args, **kwds: func(self.ant_device, *args, **kwds)


# vim: et ts=4 sts=4 nowrap
