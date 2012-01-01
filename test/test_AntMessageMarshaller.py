import unittest
from gat.ant_stream_device import AntMessageMarshaller, AntMessage

class Test(unittest.TestCase):

    def setUp(self):
        self.m = AntMessageMarshaller()

    def test_generate_checkum(self):
        self.assertEquals(0xFF, self.m.generate_checksum("\xA5\x5A"))
        self.assertEquals(0x00, self.m.generate_checksum("\xA5\x5A\xFF"))

    def test_validate_checksum(self):
        self.assertTrue(self.m.validate_checksum("\xA5\x5A\xFF"))
        self.assertTrue(self.m.validate_checksum("\xA5\x5A\xFF\x00"))
        self.assertFalse(self.m.validate_checksum("\xA5\x5A\xFF\x01"))

    def test_pack_alligment_and_endian(self):
        self.assertEquals("\x03\x01\00", self.m.marshall("BH", 0x41, [3, 1])[3:-1])
        self.assertEquals("\x03\x00\01", self.m.marshall("HB", 0x42, [3, 1])[3:-1])

    def test_calc_size(self):
        self.assertEquals("\x03", self.m.marshall("BH", 0x41, [3, 1])[1])
        self.assertEquals("\x03", self.m.marshall("HB", 0x41, [3, 1])[1])

    def test_marshall(self):
        string = self.m.marshall("x?HB", 0x41, [True, 37132, 8])
        self.assertEquals("\xA4\x05\x41\x00\x01\x0C\x91\x08", string[:-1])
        self.assertTrue(self.m.validate_checksum(string))
        
    def test_unmarshall(self):
        (sync, msg_id, args, extended_attrs) = self.m.unmarshall("x?HB", "\xA4\x05\x41\x00\x01\x0C\x91\x08\x74")
        self.assertEquals(0xA4, sync)
        self.assertEquals(0x41, msg_id)
        self.assertEquals(True, args[0])
        self.assertEquals(37132, args[1])
        self.assertEquals(8, args[2])


# vim: et ts=4 sts=4 nowrap
