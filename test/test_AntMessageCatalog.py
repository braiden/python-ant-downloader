import unittest
from gant.ant_msg_catalog import AntMessageCatalog

class Test(unittest.TestCase):
    
    def setUp(self):
        self.catalog = AntMessageCatalog([
            ("ANT_UnassignChannel", 0x41, "B", ["channelNumber"]),
            ("ANT_AssignChannel", 0x42, "BBB", ["channelNumber", "channelType", "networkNumber"]),
            ("ANT_ResetSystem", 0x4A, "x", []),
            ("ANT_OpenChannel", 0x4B, "B", ["channelNumber"]),
            ("ANT_CloseChannel", 0x4C, "B", None)])

    def test_init(self):
        self.assertEquals(5, len(self.catalog.entries))
        self.assertEquals(5, len(self.catalog.entry_by_msg_id))
        self.assertEquals("B", self.catalog.entry_by_msg_id[0x41].msg_format)
        self.assertEquals(4, self.catalog.entries[1].msg_args(*[1,4,2,]).channelType)

    def test_remove_entries(self):
        self.catalog.remove_entries([0x32, 0x42, 0x4B])
        self.assertEquals(3, len(self.catalog.entries))
        self.assertEquals(3, len(self.catalog.entry_by_msg_id))
                        

# vim: et ts=4 sts=4 nowrap
