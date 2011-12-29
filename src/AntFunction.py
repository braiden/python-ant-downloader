from struct import pack, calcsize


ANT_SYNC_TX = 0xA4
ANT_SYNC_RX = 0xA5


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
        Generate a checksum of the given input.
        Per spec xor of all data including sync.
        """
        return reduce(lambda x, y: x ^ y, map(lambda x: ord(x), msg))

    def pack(self, *args):
        """
        Return a byte array which represents the data
        needing to be written to device to execute
        operation with the provided arguments.
        """
        length = calcsize(self.arg_pack)
        data = pack("3B" + self.arg_pack, ANT_SYNC_TX, length, self.msg_id, *args)
        return data + pack("B", self.checksum(data))

    def __call__(self, device, *args):
        """
        Execute this command on the given target device.
        """
        data = self.pack(*args)
        for byte in data:
            device.write(byte)


ANT_UnassignChannel = AntFunction(0x41, "B")
ANT_AssignChannel = AntFunction(0x42, "BBB")
ANT_AssignChannelExtended = AntFunction(0x42, "BBBB")
ANT_SetChannelId = AntFunction(0x51, "B<HBB")
ANT_SetChannelPeriod = AntFunction(0x43, "B<H")
ANT_SetChannelSearchTimeout = AntFunction(0x44, "BB")
ANT_SetChannelRfFreq = AntFunction(0x45, "BB")
ANT_SetNetworkKey = AntFunction(0x46, "B8s")
ANT_SetTransmitPower = AntFunction(0x47, "xB")
ANT_AddChannelId = AntFunction(0x59, "B<HBB?")
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
