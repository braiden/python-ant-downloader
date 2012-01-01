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
        msg = AntMessage(0xA4, 0x41, [3,1], None)
        self.assertEquals("\x03\x01\00", self.m.marshall("BH", msg)[3:-1])
        self.assertEquals("\x03\x00\01", self.m.marshall("HB", msg)[3:-1])

    def test_calc_size(self):
        msg = AntMessage(0xA4, 0x41, [3,1], None)
        self.assertEquals("\x03", self.m.marshall("BH", msg)[1])
        self.assertEquals("\x03", self.m.marshall("HB", msg)[1])

    def test_marshall(self):
        msg = AntMessage(None, 0x41, [True, 37132, 8], None)
        string = self.m.marshall("x?HB", msg)
        self.assertEquals("\xA4\x05\x41\x00\x01\x0C\x91\x08", string[:-1])
        self.assertTrue(self.m.validate_checksum(string))
        
    def test_unmarshall(self):
        msg = self.m.unmarshall("x?HB", "\xA4\x05\x41\x00\x01\x0C\x91\x08\x74")
        self.assertEquals(0xA4, msg.sync)
        self.assertEquals(0x41, msg.msg_id)
        self.assertEquals(True, msg.args[0])
        self.assertEquals(37132, msg.args[1])
        self.assertEquals(8, msg.args[2])
        pass


# vim: et ts=4 sts=4 nowrap
