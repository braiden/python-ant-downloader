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


import usb.core
import usb.util
import errno
import logging
import struct
import array

_log = logging.getLogger("antd.usb")

class UsbHardware(object):
    """
    Provides access to USB based ANT chips.
    Communication is sent of a USB endpoint.
    USB based hardware with a serial bridge
    (e.g. nRF24AP1 + FTDI) is not supported.
    """
    
    def __init__(self, id_vendor=0x0fcf, id_product=0x1008, ep=1):
        for dev in usb.core.find(idVendor=id_vendor, idProduct=id_product, find_all=True):
            try:
                dev.set_configuration()
                usb.util.claim_interface(dev, 0)
                self.dev = dev
                self.ep = ep
                break
            except IOError as (err, msg):
                if err == errno.EBUSY or "Device or resource busy" in msg: #libusb10 or libusb01
                    _log.info("Found device with vid(0x%04x) pid(0x%04x), but interface already claimed.", id_vendor, id_product)
                else:
                    raise
        else:
            raise NoUsbHardwareFound(errno.ENOENT, "No available device matching vid(0x%04x) pid(0x%04x)." % (id_vendor, id_product))

    def close(self):
        usb.util.release_interface(self.dev, 0)

    def write(self, data, timeout):
        transfered = self.dev.write(self.ep | usb.util.ENDPOINT_OUT, data, timeout=timeout)
        if transfered != len(data):
            raise IOError(errno.EOVERFLOW, "Write too large, len(data) > wMaxPacketSize not supported.")

    def read(self, timeout):
        return self.dev.read(self.ep | usb.util.ENDPOINT_IN, 16384, timeout=timeout)


class NoUsbHardwareFound(IOError): pass

class SerialHardware(object):

    def __init__(self, dev="/dev/ttyUSB0", baudrate=115200):
        import serial
        self.dev = serial.Serial(port=dev, baudrate=baudrate, timeout=1)

    def close(self):
        self.dev.close()

    def write(self, data, timeout):
        arr = array.array("B", data)
        self.dev.write(arr.tostring())

    def read(self, timeout):
        # attempt to read the start of packet
        header = self.dev.read(2)
        if header:
            sync, length = struct.unpack("2B", header)
            if sync not in (0xa4, 0xa5):
                raise IOError(-1, "ANT packet did not start with expected SYNC packet. Remove USB device and try again?")
            length += 2 # checksum & msg_id
            data = self.dev.read(length)
            if len(data) != length:
                raise IOError(-1, "ANT packet short?")
            return array.array("B", header + data)
        else:
            raise IOError(errno.ETIMEDOUT, "Timeout")

# vim: ts=4 sts=4 et
