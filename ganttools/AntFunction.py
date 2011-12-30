from struct import pack, unpack, calcsize
from collections import namedtuple

ANT_SYNC_TX = 0xA4
ANT_SYNC_RX = 0xA5

class AntFunction(object):
    """
    An instance of AntFunction encapsulates an
    ANT message function defined in section 9.3
    of protocol specification.
    """

    def __init__(self, msg_id, args, arg_names=None):
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
        data = pack("<3B" + self.args, ANT_SYNC_TX, length, self.msg_id, *args)
        return data + pack("B", self.checksum(data))

    def unpack(self, msg):
        """
        Unpack the give message to its arguments.
        """
        return unpack("<BBB" + self.args + "B", msg)

    def get_args(self, msg):
        """
        Return the args which were passed as part of this
        message. If a namedtuple was provided, the returned
        object will also have args availible by name.
        """
        tokens = self.unpack(msg)
        if tokens[2] == self.msg_id:
            arg_names = self.arg_names or self.create_default_arg_names(len(tokens) - 4)
            cmd = arg_names(*tokens[3:-1])
            return cmd

    def disasm(self, msg):
        """
        Return a string descriping the provided message
        and its arguments. Will return None if the message
        is not known by this function.
        """
        tokens = self.unpack(msg)
        if tokens[2] == self.msg_id:
            sync = "<<" if tokens[0] == ANT_SYNC_TX else ">>"
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


ANT_UnassignChannel = AntFunction(0x41, "B")
ANT_AssignChannel = AntFunction(0x42, "BBB")
ANT_AssignChannelExtended = AntFunction(0x42, "BBBB")
ANT_SetChannelId = AntFunction(0x51, "BHBB")
ANT_SetChannelPeriod = AntFunction(0x43, "BH")
ANT_SetChannelSearchTimeout = AntFunction(0x44, "BB")
ANT_SetChannelRfFreq = AntFunction(0x45, "BB")
ANT_SetNetworkKey = AntFunction(0x46, "B8s")
ANT_SetTransmitPower = AntFunction(0x47, "xB")
ANT_AddChannelId = AntFunction(0x59, "BHBB?")
ANT_ConfigList = AntFunction(0x5A, "BBB")
ANT_SetChannelTxPower = AntFunction(0x60, "BB")
ANT_SetLowPriorityChannelSearchTimeout = AntFunction(0x63, "BB")
ANT_SetSerialNumChannelId = AntFunction(0x65, "BBB")
ANT_RxExtMesgsEnable = AntFunction(0x66, "x?")
ANT_EnableLed = AntFunction(0x68, "x?")
ANT_CrystalEnable = AntFunction(0x6D, "x")
ANT_LibConfig = AntFunction(0x6E, "xB")
ANT_ConfigFrequencyAgility = AntFunction(0x70, "BBBB")
ANT_SetProximitySearch = AntFunction(0x71, "BB")
ANT_SetChannelSearchPriority = AntFunction(0x75, "BB")

# vim: et ts=4 sts=4
