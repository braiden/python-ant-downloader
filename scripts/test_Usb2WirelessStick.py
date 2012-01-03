#!/usr/bin/env python

# just sends some commands to usb device and print response

import logging
from gant.ant_usb_device import AntUsbHardware, AntUsbDevice
from gant.ant_stream_device import AntExtendedMessageMarshaller
from gant.ant_msg_catalog import ANT_FUNCTION_CATALOG, ANT_CALLBACK_CATALOG

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s %(message)s")

log = logging.getLogger()

hardware = AntUsbHardware(idVendor=0x0fcf, idProduct=0x1008)
marshaller = AntExtendedMessageMarshaller()
device = AntUsbDevice(hardware, marshaller, ANT_FUNCTION_CATALOG, ANT_CALLBACK_CATALOG)

def drain(timeout=100):
    while True:
        msg = device._read(timeout=timeout)
        try:
            if msg: log.debug(">> " + str(device.disasm_input_msg(msg)))
            else: break
        except:
            log.debug(">> " + msg.encode("hex"))

drain(timeout=100)
device.resetSystem()
drain(timeout=100)
device.resetSystem()
drain(timeout=100)

hardware.close()

# vim: et ts=4 sts=4 nowrap
