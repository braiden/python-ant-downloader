#!/usr/bin/python

import unittest
from collections import namedtuple
from ganttools.antcore import AntFunction

class Test(unittest.TestCase):

    def test_pack_and_unpack(self):
        function = AntFunction(0xA4, 0xC3, "BBBB") 
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
        function = AntFunction(0xA4, 0xAA, "H?", namedtuple("ANT_EnableChannel", ["channelNumber","enabled"]))
        msg1 = function.pack(channelNumber=1, enabled=False)
        msg2 = function.pack(1, False)
        self.assertEquals(msg1, msg2)

    def test_output_is_little_endian_and_standard_size(self):
        function = AntFunction(0xA4, 0xAB, "H")
        msg = function.pack(0xAADD)
        self.assertEquals(0xDD, ord(msg[3]))
        self.assertEquals(0xAA, ord(msg[4]))

    def test_get_args(self):
        function = AntFunction(0xA4, 0xAA, "H?", namedtuple("ANT_EnableChannel", ["channelNumber","enabled"]))
        msg = function.pack(channelNumber=1, enabled=False)
        args = function.get_args(msg)
        self.assertEquals(1, args.channelNumber)
        self.assertEquals(1, args[0])
        function = AntFunction(0xA4, 0xAA, "H?")
        args = function.get_args(msg)
        self.assertEquals(1, args.arg0)
        self.assertEquals(1, args[0])

    def test_string_is_not_processed_as_unicode(self):
        function = AntFunction(0xA4, 0x00, "BB")
        self.assertEquals(
                function.pack(0xD4, 0x8F)[-1],
                function.pack(0x8F, 0xD4)[-1])

    def test_is_supported(self):
        function = AntFunction(0xA4, 0x51, "BHBB")
        packed = function.pack(23, 2422, 0x43, 0x12)
        self.assertTrue(function.is_supported(packed))

    def test_disasm(self):
        function = AntFunction(0xA4, 0x51, "BHBB",
                namedtuple("ANT_SetChannelId", "channelNumber, deviceNumber, deviceTypeId, transType"))
        packed = function.pack(27, 41902, 0x80, 0x40)
        data = function.disasm(packed)
        self.assertEquals(0xA4, data[0])
        self.assertEquals(5, data[1])
        self.assertEquals(0x51, data[2])
        self.assertEquals(0x26, data[4])

    def test_struct_is_packed(self):
        function1 = AntFunction(0x00, 0x00, "BH")
        function2 = AntFunction(0x00, 0x00, "HB")
        msg1 = function1.pack(1,1)
        msg2 = function2.pack(1,1,)
        self.assertEquals(len(msg1), len(msg2))
        self.assertEquals(7, len(msg1))
        self.assertEquals(3, ord(msg1[1]))
        self.assertEquals(3, ord(msg2[1]))

    def test_verify_checksum(self):
        f = AntFunction(0, 0, "x")
        self.assertTrue(f.verify_checksum("\x00\x00"))
        self.assertFalse(f.verify_checksum("\x00\x01"))

    def test_calculated_checksum(self):
        f = AntFunction(0x00, 0x00, "BxB")
        m = f.pack(0xAB, 0x93)
        self.assertEquals(0xAB ^ 0x93 ^ 3, ord(m[-1]))

    def test_ignore_extended_data_on_unpack(self):
        f = AntFunction(0xA5, 0x20, "BBH")
        m = "\xA5\x06\x20\xAA\xFF\x01\x00\x00\x00\x00"
        self.assertTrue(f.is_supported(m))
        self.assertTrue(f.is_extended(m))
        self.assertEquals("\xA5\x06\x20\xAA\xFF\x01\x00\x00", f.remove_extended_data_bytes(m))
        data = f.unpack(m)
        self.assertEquals(0xAA, data[3])
        self.assertEquals(0xFF, data[4])
        self.assertEquals(0x01, data[5])

    def test_get_extended_data_bytes(self):
        f = AntFunction(0xA5, 0x20, "BBH")
        m = "\xA5\x06\x20\xAA\xFF\x01\x00\x07\x08\x00"
        self.assertTrue(f.is_supported(m))
        self.assertTrue(f.is_extended(m))
        data = f.get_extended_data_bytes(m)
        self.assertEquals("\x07\x08", data)

# vim: et ts=4 sts=4
