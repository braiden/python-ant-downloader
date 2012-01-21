# Copyright (c) 2012, Braiden Kindt.
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
# 
#   1. Redistributions of source code must retain the above copyright
#      notice, this list of conditions and the following disclaimer.
# 
#   2. Redistributions in binary form must reproduce the above
#      copyright notice, this list of conditions and the following
#      disclaimer in the documentation and/or other materials
#      provided with the distribution.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDER AND CONTRIBUTORS
# ''AS IS'' AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY
# WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

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
