import mock
import unittest
import array

import gant.ant_usb_hardware
from gant.ant_usb_hardware import *

backend = mock.Mock()
gant.ant_usb_hardware._backend = backend


class TestUsbHardware(unittest.TestCase):

    def setUp(self):
        backend.reset_mock()
        dev1 = mock.Mock()
        dev2 = mock.Mock()
        dev3 = mock.Mock()
        dev1.idProduct = 1
        dev1.idVendor = 1
        dev2.idProduct = 2
        dev2.idVendor = 1
        dev3.idProduct = 1
        dev3.idVendor = 1
        backend.enumerate_devices.return_value = (dev1, dev2, dev3)
        backend.get_device_descriptor = lambda el : el

    def test_find_usb_devices(self):
        self.assertEquals(2 , len([d for d in find_usb_devices(1, 1)]))
        self.assertEquals(1 , len([d for d in find_usb_devices(2, 1)]))
        self.assertEquals(0 , len([d for d in find_usb_devices(3, 1)]))
        
    def test_init(self):
        handle = mock.Mock()
        backend.open_device.return_value = handle
        dev = UsbHardware(1, 1)
        backend.set_configuration.assert_called_with(handle, 1)
        backend.claim_interface.assert_called_with(handle, 0)
        backend.set_interface_altsetting.assert_called_with(handle, 0, 0)
        self.assertEquals(handle, dev._handle)

    def test_dont_invoke_backend_after_close(self):
        dev = UsbHardware(1, 1)
        dev.close()
        dev.close()
        dev.read()
        dev.write("")
        self.assertEquals(1, backend.close_device.call_count)
        self.assertTrue(backend.bulk_read.called is False)
        self.assertTrue(backend.bulk_write.called is False)

    def test_write(self):
        dev = UsbHardware(1, 1)
        dev.write("", timeout=13)
        backend.bulk_write.assert_called_with(dev._handle, 1, 0, array.array("b", ""), 13)

    def test_read(self):
        dev = UsbHardware(1, 1)
        backend.bulk_read.return_value = array.array("b", "test")
        self.assertEquals("test", dev.read(size=1024, timeout=34))
        backend.bulk_read.return_value = None
        self.assertEquals("", dev.read(size=32, timeout=23))


# vim: et ts=4 sts=4
