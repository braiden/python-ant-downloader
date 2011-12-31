import unittest
from gat.ant_msg_catalog import AntMessageCatalog

class Test(unittest.TestCase):
    
    def test_init(self):
        catalog = AntMessageCatalog(
                [   ("ANT_UnassignChannel", 0x41, "B", ["channelNumber"]),
                    ("ANT_AssignChannel", 0x42, "BBB", ["channelNumber", "channelType", "networkNumber"]),],
                [   ("ANT_ResetSystem", 0x4A, "x", []),
                    ("ANT_OpenChannel", 0x4B, "B", ["channelNumber"]),
                    ("ANT_CloseChannel", 0x4C, "B", ["channelNumber"]),])
        self.assertEquals(2, len(catalog.functions))
        self.assertEquals(3, len(catalog.callbacks))
        self.assertEquals(2, len(catalog.function_by_msg_id))
        self.assertEquals(3, len(catalog.callback_by_msg_id))
        self.assertEquals(5, len(catalog.entry_by_msg_id))
        self.assertEquals("B", catalog.entry_by_msg_id[0x41].msg_format)
        catalog.functions[0].msg_args(channelNumber=1)
        catalog.callbacks[0].msg_args()
                        

# vim: et ts=4 sts=4 nowrap
