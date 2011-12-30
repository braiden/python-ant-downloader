#!/usr/bin/python

import unittest
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


if __name__ == "__main__":
    unittest.main()

# vim: et ts=4 sts=4
