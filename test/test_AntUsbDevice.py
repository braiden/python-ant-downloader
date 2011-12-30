import unittest
from ganttools.antdevice import AntUsbDevice

class Test(unittest.TestCase):

    def test_find_device(self):
        dev = AntUsbDevice(idVendor=0x0fcf, idProduct=0x1008)


# vim: et ts=4 sts=4 nowrap
