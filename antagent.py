#!/usr/bin/python

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

import logging
import sys
import time
import struct
import argparse
import os

import antagent
import antagent.garmin as garmin

parser = argparse.ArgumentParser()
parser.add_argument("--dir", "-d", type=str, nargs=1, 
        default=os.path.expanduser("~/.ant-agent"),
        help="directory containing saved data, default ~/.antagent/")
parser.add_argument("--verbose", "-v", action="count",
        help="verbose, and extra -v's to increase verbosity")
parser.add_argument("--continuous", "-c", action="store_const", const=True,
        help="run in continuous search mode downloading data from any availible devices, WILL NOT PAIR WITH NEW DEVICES")
parser.add_argument("--retry", "-r", type=int, nargs=1, default=3, metavar="n",
        help="how many times should data download be attempt before failure, multiple tries may be neccessary if operating in poor RF environment.")
args = parser.parse_args()

logging.basicConfig(
        level=logging.INFO,
        out=sys.stderr,
        format="[%(threadName)s]\t%(asctime)s\t%(levelname)s\t%(message)s")

if args.verbose:
    logging.getLogger("antagent.garmin").setLevel(logging.DEBUG)
    if args.verbose > 1:
        logging.getLogger("antagent.antfs").setLevel(logging.DEBUG)
    if args.verbose > 2:
        logging.getLogger("antagent.ant").setLevel(logging.DEBUG)

_log = logging.getLogger()

host = antagent.UsbAntFsHost()

def dump_packet(packet, file):
    pid, length, data = packet
    file.write(struct.pack("<HH", pid, length))
    if data: file.write(data.raw)

def dump_list(data, file):
        for packet in data:
            try:
                dump_list(packet, file)
            except TypeError:
                dump_packet(packet, file)

try:
    failed_count = 0
    while failed_count <= args.retry:
        try:
            _log.info("Searching for ANT devices...")
            beacon = host.search()
            if beacon and beacon.data_availible:
                _log.info("Linking...")
                host.link()
                _log.info("Pairing with device...")
                host.auth(pair=not args.continuous)
                with open(time.strftime("%Y%m%d-%H%M%S.raw"), "w") as file:
                    _log.info("Dumping data to %s.", file.name)
                    dev = garmin.Device(host)
                    dump_list(dev.get_product_data(), file)
                    runs = dev.get_runs()
                    dump_list(runs, file)
                _log.info("Closing session...")
                host.disconnect()
                if not args.continuous: break
                failed_count = 0
        except antagent.AntError:
            failed_count += 1
            _log.warning("Caught error while communicating with device, will retry.", exc_info=True) 
finally:
    try: host.close()
    except Exception: _log.warning("Failed to cleanup resources on exist.", exc_info=True)

# vim: ts=4 sts=4 et
