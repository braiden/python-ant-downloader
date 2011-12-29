# ANT message spec defined in "ANT Messages Protocol and Usage" Rev 4.5

from struct import pack

class AntFunction(object):
    """
    An instance of AntFunction encapsulates an
    ANT message function defined in section 9.3
    of protocol specification.
    """

    def __init__(self, msg_id, arg_pack):
        """
        Create a new AntFunction with the given MSG ID
        arg_pack is the python struct.pack format string matching
        the arguments defined in ant specification.
        """
        self.msg_id = msg_id
        self.arg_pack = arg_pack
        
    def checksum(self, msg):
        """
        Generate a check sum of the given input.
        Per spec, xorg of all data including sync
        """
        return reduce(lambda x, y: x ^ y, msg) & 0xFF

    def pack(self, *args):
        """
        Return a byte array which represents the data
        needing to be written to device where the give args.
        """
        data = bytearray(pack(self.arg_pack, *args))
        sync = 0xA4
        length = len(data)
        header = bytearray(pack("BBB", sync, length, self.msg_id))
        header.extend(data)
        checksum = self.checksum(header)
        header.append(checksum)
        return header

    def execute(self, sink, *args):
        """
        Execute this command on the given target (sink)
        """
        data = self.pack(*args)
        if sink:
            for byte in data:
                sink.write(byte)
        return data

    def __call__(self, sink, *args):
        return self.execute(sink, *args)


ANT_UnassignChannel = AntFunction(0x41, "B")
ANT_AssignChannel = AntFunction(0x42, "BBB")
ANT_AssignChannelExtended = AntFunction(0x42, "BBBB")
ANT_SetChannelId = AntFunction(0x51, "B<HBB")
ANT_SetChannelPeriod = AntFunction(0x43, "B<H")
ANT_SetChannelSearchTimeout = AntFunction(0x44, "BB")
ANT_SetChannelRfFreq = AntFunction(0x45, "BB")
ANT_SetNetworkKey = AntFunction(0x46, "B8s")
ANT_AddChannelId = AntFunction(0x59, "B<HBBB")
ANT_ConfigList = AntFunction(0x5A, "BBB")
ANT_SetChannelTxPower = AntFunction(0x60, "BB")
ANT_SetLowPriorityChannelSearchTimeout(0x63, "BB")

# vim: et ts=4 sts=4
