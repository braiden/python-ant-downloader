#!/usr/bin/python

import unittest
from collections import namedtuple
from ganttools.AntFunction import AntFunction

class Test(unittest.TestCase):

    def test_pack_and_unpack(self):
        function = AntFunction(0xC3, "BBBB") 
        packed_string = function.pack(0x01, 0x02, 0x03, 0x04)
        args = function.unpack(packed_string)
        self.assertEquals(8, len(args))
        self.assertEquals(0xA4, args[0])
        self.assertEquals(0x04, args[1])
        self.assertEquals(0xC3, args[2])
        self.assertEquals(0x01, args[3])
        self.assertEquals(0x02, args[4])
        self.assertEquals(0x03, args[5])
        self.assertEquals(0x04, args[6])
        self.assertEquals(0x67, args[7])

    def test_named_args(self):
        function = AntFunction(0xAA, "H?", namedtuple("ANT_EnableChannel", ["channelNumber","enabled"]))
        msg1 = function.pack(channelNumber=1, enabled=False)
        msg2 = function.pack(1, False)
        self.assertEquals(msg1, msg2)

    def test_output_is_little_endian_and_standard_size(self):
        function = AntFunction(0xAB, "H")
        msg = function.pack(0xAADD)
        self.assertEquals(0xDD, ord(msg[3]))
        self.assertEquals(0xAA, ord(msg[4]))

    def test_get_args(self):
        function = AntFunction(0xAA, "H?", namedtuple("ANT_EnableChannel", ["channelNumber","enabled"]))
        msg = function.pack(channelNumber=1, enabled=False)
        args = function.get_args(msg)
        self.assertEquals(1, args.channelNumber)
        self.assertEquals(1, args[0])
        function = AntFunction(0xAA, "H?")
        args = function.get_args(msg)
        self.assertEquals(1, args.arg0)
        self.assertEquals(1, args[0])

    def test_string_is_not_processed_as_unicode(self):
        function = AntFunction(0x00, "BB")
        self.assertEquals(
                function.pack(0xD4, 0x8F)[-1],
                function.pack(0x8F, 0xD4)[-1])

    def test_disasm(self):
        function = AntFunction(0x51, "BHBB",
                namedtuple("ANT_SetChannelId", "channelNumber, deviceNumber, deviceTypeId, transType"))
        packed = function.pack(27, 41902, 0x80, 0x40)
        string = function.disasm(packed)
        self.assertEquals(
                "<< ANT_SetChannelId(channelNumber=27, deviceNumber=41902, " + 
                "deviceTypeId=128, transType=64) data_bytes=6 checksum(actual/derived)=37/37",
                string)

# vim: et ts=4 sts=4
