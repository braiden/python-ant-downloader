import unittest
from gat.ant_stream_device import AntStreamDeviceBase
from gat.ant_msg_catalog import AntMessageCatalog

class Test(unittest.TestCase):

    def setUp(self):
        self.catalog = AntMessageCatalog(
                [   ("ANT_UnassignChannel", 0x41, "B", ["channelNumber"]),
                    ("ANT_AssignChannel", 0x42, "BBB", ["channelNumber", "channelType", "networkNumber"]),],
                [   ("ANT_ResetSystem", 0x4A, "x", []),
                    ("ANT_OpenChannel", 0x4B, "B", ["channelNumber"]),
                    ("ANT_CloseChannel", 0x4C, "B", ["channelNumber"]),])
        self.marshaller = MockAntMessageMarshaller()
        self.device = MockAntStreamDevice(self.catalog, self.marshaller)

    def test_exec_function(self):
        self.device.exec_function(0x42, 1, 3, 8)
        self.assertEquals("BBB", self.marshaller.pack_format)
        self.assertEquals(0x42, self.device.msg.msg_id)

    def test_exec_function_by_kwd(self):
        self.device.exec_function(0x42, channelNumber=1, channelType=3, networkNumber=8)
        self.assertEquals("BBB", self.marshaller.pack_format)
        self.assertEquals(0x42, self.device.msg.msg_id)
        self.assertEquals(3, self.device.msg.args.channelType)

    def test_enhance(self):
        self.device.ANT_UnassignChannel(3)
        self.assertEquals(0x41, self.device.msg.msg_id)
        self.assertEquals("B", self.marshaller.pack_format)


class MockAntMessageMarshaller(object):

    def marshall(self, pack_format, msg):
        self.pack_format = pack_format
        return msg


class MockAntStreamDevice(AntStreamDeviceBase):

    def __init__(self, catalog, marshaller):
        super(MockAntStreamDevice, self).__init__(catalog, marshaller)
        self.disasm = self._disasm 

    def _disasm(self, msg):
        return msg;

    def _write(self, msg, timeout=100):
        self.msg = msg


# vim: et ts=4 sts=4 nowrap
