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
parser.add_argument("--config", "-c", nargs=1, metavar="f", type=argparse.FileType('r'),
        help="use provided configuration, defaults: %s" % ", ".join(antagent.cfg.DEFAULT_CONFIG_LOCATIONS))
parser.add_argument("--daemon", "-d", action="store_const", const=True,
        help="run in continuous search mode downloading data from any availible devices, WILL NOT PAIR WITH NEW DEVICES")
parser.add_argument("--verbose", "-v", action="store_const", const=True,
        help="enable all debugging output, NOISY: see config file to selectively enable loggers")
args = parser.parse_args()

cfg_locations = antagent.cfg.DEFAULT_CONFIG_LOCATIONS + [f.name for f in args.config or []] 
if not antagent.cfg.read(cfg_locations):
    print "unable to read config file from %s" % antagent.cfg.DEFAULT_CONFIG_LOCATIONS
    parser.print_usage()
    sys.exit(1)

if args.verbose: antagent.cfg.init_loggers(logging.DEBUG)
_log = logging.getLogger("antagent")

def export_tcx(raw_file_name):
    with open(raw_file_name) as file:
        host = antagent.garmin.MockHost(file.read())
        device = antagent.garmin.Device(host)
        run_pkts = device.get_runs()
        runs = antagent.garmin.extract_runs(device, run_pkts)
        for run in runs:
            tcx_name = time.strftime("%Y%m%d-%H%M%S.tcx", run.time.gmtime)
            tcx_full_path = antagent.cfg.get_path("tcx_output_dir", tcx_name)
            _log.info("Writing %s.", tcx_full_path)
            with open(tcx_full_path, "w") as file:
                doc = antagent.tcx.create_document([run])
                file.write(etree.tostring(doc, pretty_print=True, xml_declaration=True, encoding="UTF-8"))


host = antagent.cfg.create_antfs_host()
try:
    failed_count = 0
    while failed_count <= antagent.cfg.get_retry():
        try:
            _log.info("Searching for ANT devices...")
            beacon = host.search(stop_after_first_device=not args.daemon)
            if beacon and beacon.data_availible:
                _log.info("Device has data. Linking...")
                host.link()
                _log.info("Pairing with device...")
                client_id = host.auth(pair=not args.daemon)
                antagent.cfg.set_device_sn(client_id)
                raw_name = time.strftime("%Y%m%d-%H%M%S.raw")
                raw_full_path = antagent.cfg.get_path("raw_output_dir", raw_name)
                with open(raw_full_path, "w") as file:
                    _log.info("Saving raw data to %s.", file.name)
                    dev = antagent.Device(host)
                    antagent.garmin.dump(file, dev.get_product_data())
                    runs = dev.get_runs()
                    antagent.garmin.dump(file, runs)
                _log.info("Closing session...")
                host.disconnect()
                try:
                    export_tcx(raw_full_path)
                except Exception:
                    _log.error("Failed to create TCX, device may be unsupported.", exc_info=True)
            elif not args.daemon:
                _log.info("Found device, but no data availible for download.")
            if not args.daemon: break
            failed_count = 0
        except antagent.AntError:
            _log.warning("Caught error while communicating with device, will retry.", exc_info=True) 
            failed_count += 1
finally:
    try: host.close()
    except Exception: _log.warning("Failed to cleanup resources on exist.", exc_info=True)


# vim: ts=4 sts=4 et
