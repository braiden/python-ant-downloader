import unittest
import struct
from gat.ant_msg_catalog import AntMessageCatalog
from gat.ant_stream_device import AntStreamDevice, AntMessageMarshaller

class Test(unittest.TestCase):

    def setUp(self):
        self.catalog = AntMessageCatalog([
                ("ANT_UnassignChannel", 0x41, "B", ["channelNumber"]),
                ("ANT_AssignChannel", 0x42, "BBB", ["channelNumber", "channelType", "networkNumber"]),
                ("ANT_ResetSystem", 0x4A, "x", []),
                ("ANT_OpenChannel", 0x4B, "B", None),
                ("ANT_CloseChannel", 0x4C, "B", ["channelNumber"])])
        self.hardware = MockAntHardware()
        self.device = AntStreamDevice(self.hardware, AntMessageMarshaller(), self.catalog, self.catalog) 
        self.asm = self.device._asm
        self.disasm = self.device._disasm

    def test_read(self):
        self.hardware.read_queue = ["\xA4\x05\x40", "\x00" * 6]
        msg = self.device._read()
        self.assertEquals("\xA4\x05\x40\x00\x00\x00\x00\x00\x00", msg)
        old_msg = msg
        self.hardware.read_queue = msg
        msg = self.device._read()
        self.assertEquals(old_msg, msg)


    def test_exec_function_args(self):
        self.device.exec_function(0x42, 1, 3, 8)
        self.assertEquals("\xA4\x03\x42\x01\x03\x08\xEF", self.hardware.msg)
        self.device.exec_function(0x42, channelNumber=1, channelType=3, networkNumber=8)
        self.assertEquals("\xA4\x03\x42\x01\x03\x08\xEF", self.hardware.msg)

    def test_enance(self):
        self.device.ANT_AssignChannel(channelNumber=1, channelType=3, networkNumber=8)
        self.assertEquals("\xA4\x03\x42\x01\x03\x08\xEF", self.hardware.msg)
        self.device.ANT_ResetSystem()
        self.assertEquals("\xA4\x01\x4A\x00\xEF", self.hardware.msg)

    def test_asm(self):
        m1 = self.asm(self.catalog, 0x42, [], {"channelNumber": 3, "channelType": 0x40, "networkNumber": 8})
        self.assertEquals(m1[:-1], "\xA4\x03\x42\x03\x40\x08")
        m2 = self.asm(self.catalog, 0x42, [3, 0x40, 8], {})
        self.assertEquals(m1, m2)
        # invalid type should raise error
        try: self.asm(self.catalog, 0xFF, [], {})
        except KeyError: pass
        else: self.fail()
        # invalid ard should raise error
        try: self.asm(self.catalog, 0x41, [], {"unkownArg": 3})
        except TypeError: pass
        else: self.fail()
        # wrong number of args should raise error
        try: self.asm(self.catalog, 0x41, [], {})
        except struct.error: pass
        else :self.fail()

    def test_disasm(self):
        # good message with named args + valid checksum
        m = self.disasm(self.catalog, "\xA4\x03\x42\x04\x03\x40\xA2")
        self.assertEquals(m.sync, 0xA4)
        self.assertEquals(m.msg_id, 0x42)
        self.assertEquals(m.args.channelType, 0x03)
        self.assertEquals(m.args[2], 0x40)
        # good message but no named args availible
        m = self.disasm(self.catalog, "\xA5\x01\x4B\x04\xEB")
        self.assertEquals(m.sync, 0xA5)
        self.assertEquals(m.msg_id, 0x4B)
        self.assertEquals(m.args[0], 0x04)
        # unkown message format should fail
        try: self.disasm(self.catalog, "\xAB\x01\xBB\x00\x11")
        except KeyError: pass
        else: self.fail()
        # bad crc should fail
        try: self.disasm(self.catalog, "\xA5\x01\x4B\x04\xEC")
        except AssertionError: pass
        else: self.fail()


class MockAntHardware(object):
    
    def write(self, msg, timeout=100):
        self.msg = msg

    def read(self, n, timeout=100):
        result = self.read_queue[0]
        self.read_queue = self.read_queue[1:]
        return result
        

# vim: et ts=4 sts=4 nowrap
