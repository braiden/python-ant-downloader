import unittest
from gat.ant_msg_catalog import AntMessageCatalog
from gat.ant_stream_device import AntStreamDevice

class Test(unittest.TestCase):

    def setUp(self):
        self.assembler = MockAntMessageAssembler()
        self.hardware = MockAntHardware()
        self.device = AntStreamDevice(self.hardware, self.assembler)

    def test_exec_function_args(self):
        self.device.exec_function(0x42, 1, 3, 8, channelNumber=2)
        self.assertEquals(self.assembler.msg_id, 0x42)
        self.assertEquals(self.assembler.args, (1, 3, 8))
        self.assertEquals(self.assembler.kwds, {"channelNumber": 2})
        self.assertEquals(self.hardware.msg, (0x42, (1, 3, 8), {"channelNumber": 2}))

    def test_enance(self):
        catalog = AntMessageCatalog(
                [   ("ANT_UnassignChannel", 0x41, "B", ["channelNumber"]),
                    ("ANT_AssignChannel", 0x42, "BBB", ["channelNumber", "channelType", "networkNumber"]),],
                [   ("ANT_ResetSystem", 0x4A, "x", []),
                    ("ANT_OpenChannel", 0x4B, "B", ["channelNumber"]),
                    ("ANT_CloseChannel", 0x4C, "B", ["channelNumber"]),])
        self.device.enhance(catalog)
        self.device.ANT_AssignChannel(1,0x40,0)
        self.assertEquals(self.hardware.msg, (0x42, (1, 0x40, 0), {}))


class MockAntMessageAssembler(object):

    def asm(self, msg_id, *args, **kwds):
        self.msg_id = msg_id
        self.args = args
        self.kwds = kwds
        return (msg_id, args, kwds)

    def disasm(self, msg, lieniant=False):
        return msg


class MockAntHardware(object):
    
    def write(self, msg, timeout=100):
        self.msg = msg


# vim: et ts=4 sts=4 nowrap
