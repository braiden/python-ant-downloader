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

def downloader():
    import logging
    import sys
    import time
    import struct
    import argparse
    import os
    import dbm
    import shutil
    import lxml.etree as etree
    import antd
    
    # command line
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", "-c", nargs=1, metavar="f", type=argparse.FileType('r'),
            help="use provided configuration, defaults to ~/.antd/antd.cfg")
    parser.add_argument("--daemon", "-d", action="store_const", const=True,
            help="run in continuous search mode downloading data from any availible devices, WILL NOT PAIR WITH NEW DEVICES")
    parser.add_argument("--verbose", "-v", action="store_const", const=True,
            help="enable all debugging output, NOISY: see config file to selectively enable loggers")
    parser.add_argument("--force", "-f", action="store_const", const=True,
            help="force a connection with device even if it claims no data availible. FOR DEBUG ONLY.")
    args = parser.parse_args()
    
    # load configuration
    cfg = args.config[0] if args.config else None
    if not antd.cfg.read(cfg):
        print "unable to read config file." 
        parser.print_usage()
        sys.exit(1)
    
    # enable debug if -v used
    if args.verbose: antd.cfg.init_loggers(logging.DEBUG)
    _log = logging.getLogger("antd")
    
    # register plugins, add uploaders and file converters here
    antd.plugin.register_plugins(
        antd.cfg.create_garmin_connect_plugin(),
        antd.cfg.create_tcx_plugin()
    )
    
    # create an ANTFS host from configuration
    host = antd.cfg.create_antfs_host()
    try:
        failed_count = 0
        while failed_count <= antd.cfg.get_retry():
            try:
                _log.info("Searching for ANT devices.")
                # in daemon mode we do not attempt to pair with unkown devices
                # (it requires gps watch to wake up and would drain battery of
                # any un-paired devices in range.)
                beacon = host.search(include_unpaired_devices=not args.daemon,
                                     include_devices_with_no_data=args.force or not args.daemon)
                if beacon and (beacon.data_availible or args.force):
                    _log.info("Device has data. Linking.")
                    host.link()
                    _log.info("Pairing with device.")
                    client_id = host.auth(pair=not args.daemon)
                    raw_name = time.strftime("%Y%m%d-%H%M%S.raw")
                    raw_full_path = antd.cfg.get_path("antd", "raw_output_dir", raw_name, 
                                                      {"device_id": hex(host.device_id)})
                    with open(raw_full_path, "w") as file:
                        _log.info("Saving raw data to %s.", file.name)
                        # create a garmin device, and initialize its
                        # ant initialize its capabilities.
                        dev = antd.Device(host)
                        antd.garmin.dump(file, dev.get_product_data())
                        # download runs
                        runs = dev.get_runs()
                        antd.garmin.dump(file, runs)
                    _log.info("Closing session.")
                    host.disconnect()
                    _log.info("Excuting plugins.")
                    # dispatcher data to plugins
                    antd.plugin.publish_data(host.device_id, "raw", [raw_full_path])
                elif not args.daemon:
                    _log.info("Found device, but no data availible for download.")
                if not args.daemon: break
                failed_count = 0
            except antd.AntError:
                _log.warning("Caught error while communicating with device, will retry.", exc_info=True) 
                failed_count += 1
    finally:
        try: host.close()
        except Exception: _log.warning("Failed to cleanup resources on exist.", exc_info=True)
    
    
# vim: ts=4 sts=4 et
