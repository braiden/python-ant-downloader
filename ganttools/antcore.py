from struct import pack, unpack, calcsize
from collections import namedtuple
from ganttools import antdefs

class AntFunction(object):
    """
    An instance of AntFunction encapsulates an
    ANT message function defined in section 9.3
    of protocol specification.
    """

    def __init__(self, sync, msg_id, args, arg_names=None):
        """
        Create a new AntFunction with the given MSG ID
        args is the python struct.pack format string matching
        the arguments defined in ant specification.
        Third argument can provide a namedtuple which describse
        this function and its arguments. This is optional, and
        is mainly intended to for pretty-printing trace data
        captures from windows driver. But, providing a named
        tuple also allows for keyword args instead of positional.
        """
        self.sync = sync
        self.msg_id = msg_id
        self.args = args
        self.arg_names = arg_names
        
    def checksum(self, msg):
        """
        Generate a checksum of the given input.
        Per spec xor of all data including sync.
        """
        return reduce(lambda x, y: x ^ y, map(lambda x: ord(x), msg))

    def pack(self, *args, **kwds):
        """
        Return a byte array which represents the data
        needing to be written to device to execute
        operation with the provided arguments.
        """
        if kwds and self.arg_names:
            args = self.arg_names(**kwds)
        length = calcsize(self.args)
        data = pack("<3B" + self.args, self.sync, length, self.msg_id, *args)
        return data + pack("B", self.checksum(data))

    def unpack(self, msg):
        """
        Unpack the give message to its arguments.
        """
        return unpack("<BBB" + self.args + "B", msg)

    def is_supported(self, msg):
        """
        Return true if the provided string is a serialized
        representation of this function's output
        """
        tokens = self.unpack(msg)
        return tokens[0] == self.sync and tokens[2] == self.msg_id

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
        Return a string descriping the provided message
        and its arguments. Will return None if the message
        is not known by this function.
        """
        if self.is_supported(msg):
            tokens = self.unpack(msg)
            sync = "<<" if tokens[0] == antdefs.ANT_SYNC_TX else ">>"
            length = tokens[1]
            cmd = self.get_args(msg)
            msg_checksum = tokens[-1]
            expected_checksum = self.checksum(msg[:-1])
            return "%s %s data_bytes=%d checksum(actual/derived)=%d/%d" % (
                    sync, cmd, length, msg_checksum, expected_checksum)

    def create_default_arg_names(self, size):
        return namedtuple("ANT_0x%x" % self.msg_id, map(lambda n: "arg%d" % n, range(0, size)))

    def __call__(self, device, *args, **kwds):
        """
        Execute this command on the given target device.
        """
        data = self.pack(*args, **kwds)
        for byte in data:
            device.write(byte)

# vim: et ts=4 sts=4
