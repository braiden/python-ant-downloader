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
import dbm
import lxml.etree as etree

import antagent

parser = argparse.ArgumentParser()
parser.add_argument("--dir", "-d", type=str, nargs=1, 
        default=os.path.expanduser("~/.antagent"),
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
    logging.getLogger("antagent.tcx").setLevel(logging.DEBUG)
    if args.verbose > 1:
        logging.getLogger("antagent.antfs").setLevel(logging.DEBUG)
    if args.verbose > 2:
        logging.getLogger("antagent.ant").setLevel(logging.DEBUG)
    if args.verbose > 3:
        logging.getLogger("antagent.trace").setLevel(logging.DEBUG)

_log = logging.getLogger()

def export_tcx(raw_file_name):
    device_data_path = os.path.sep.join([args.dir, hex(client_id), "tcx"])
    if not os.path.exists(device_data_path): os.mkdir(device_data_path)
    with open(raw_file_name) as file:
        host = antagent.garmin.MockHost(file.read())
        device = antagent.garmin.Device(host)
        run_pkts = device.get_runs()
        runs = antagent.garmin.extract_runs(device, run_pkts)
        for run in runs:
            tcx_name = os.path.sep.join([device_data_path, time.strftime("%Y%m%d-%H%M%S.tcx", run.time.gmtime)])
            _log.info("Writing %s.", tcx_name)
            with open(tcx_name, "w") as file:
                doc = antagent.tcx.create_document([run])
                file.write(etree.tostring(doc, pretty_print=True, xml_declaration=True, encoding="UTF-8"))


if not os.path.exists(args.dir): os.mkdir(args.dir)
known_devices = dbm.open(args.dir + os.path.sep + "device_pairing_keys", "c")
host = antagent.UsbAntFsHost(known_devices)

try:
    failed_count = 0
    while failed_count <= args.retry:
        try:
            _log.info("Searching for ANT devices...")
            beacon = host.search(stop_after_first_device=not args.continuous)
            if beacon and beacon.data_availible:
                _log.info("Device has data. Linking...")
                host.link()
                _log.info("Pairing with device...")
                client_id = host.auth(pair=not args.continuous)
                device_data_path = os.path.sep.join([args.dir, hex(client_id), "raw"])
                if not os.path.exists(device_data_path): os.mkdir(device_data_path)
                raw_file_name = os.path.sep.join([device_data_path, time.strftime("%Y%m%d-%H%M%S.raw")])
                with open(raw_file_name, "w") as file:
                    _log.info("Saving raw data to %s.", file.name)
                    dev = antagent.Device(host)
                    antagent.garmin.dump(file, dev.get_product_data())
                    runs = dev.get_runs()
                    antagent.garmin.dump(file, runs)
                _log.info("Closing session...")
                host.disconnect()
                try:
                    export_tcx(raw_file_name)
                except Exception:
                    _log.error("Failed to create TCX, device may be unsupported.", exc_info=True)
            elif not args.continuous:
                _log.info("Found device, but no data availible for download.")
            if not args.continuous: break
            failed_count = 0
        except antagent.AntError:
            _log.warning("Caught error while communicating with device, will retry.", exc_info=True) 
            failed_count += 1
finally:
    known_devices.close()
    try: host.close()
    except Exception: _log.warning("Failed to cleanup resources on exist.", exc_info=True)


# vim: ts=4 sts=4 et
