#!/usr/bin/env python

import binascii
import argparse
from gat.ant_stream_device import AntStreamDevice, AntExtendedMessageMarshaller
from gat.ant_msg_catalog import ANT_FUNCTION_CATALOG, ANT_CALLBACK_CATALOG

parser = argparse.ArgumentParser(description="Decode nRF24AP2-USB traffic from linux usbmon from input on stdin")
parser.add_argument("file", type=file, help="Linux usbmon device (e.g. /sys/kernel/debug/usb/usbmon/8u")
parser.add_argument("bus", type=int, help="Bus number")
parser.add_argument("device", type=int, help="Device address")
args = parser.parse_args()

stream_device = AntStreamDevice(None, AntExtendedMessageMarshaller(), ANT_FUNCTION_CATALOG, ANT_CALLBACK_CATALOG)

while 1:
    line = args.file.readline()
    tokens = line.split()
    (type_and_dir, bus, device, endpoint) = tokens[3].split(":")
    if int(bus) == args.bus and int(device) == args.device and int(endpoint) == 1:
        if len(tokens) >= 7 and type_and_dir in ("Bi", "Bo") and tokens[6] == '=':
            data = binascii.unhexlify("".join(tokens[7:]))
            disasm = stream_device.disasm_output_msg if type_and_dir == "Bo" else stream_device.disasm_input_msg
            prefix = ">> " if type_and_dir == "Bo" else "<< "
            try:
                print prefix + str(disasm(data))
            except:
                print prefix + data.encode("hex")

# vim: et ts=4 sts=4 nowrap
