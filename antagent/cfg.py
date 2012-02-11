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


import ConfigParser
import dbm
import os
import binascii
import logging
import sys

_cfg = ConfigParser.SafeConfigParser()

DEFAULT_CONFIG_LOCATIONS = [
    "/etc/antagent.cfg",
    os.path.expanduser("~/.antagent/antagent.cfg"),
    "./antagent.cfg"]

def read(files):
    read = _cfg.read(files)
    if read: init_loggers()
    return read

def init_loggers(force_level=None, out=sys.stdin):
    level = force_level if force_level is not None else logging.ERROR
    logging.basicConfig(
            level=level,
            out=out,
            format="[%(threadName)s]\t%(asctime)s\t%(levelname)s\t%(message)s")
    try:
        for logger, log_level in _cfg.items("antagent.logging"):
            level = force_level if force_level is not None else logging.getLevelName(log_level)
            logging.getLogger(logger).setLevel(level) 
    except ConfigParser.NoSectionError:
        pass

def create_hardware():
    id_vendor = int(_cfg.get("antagent.hw", "id_vendor"), 0)
    id_product = int(_cfg.get("antagent.hw", "id_product"), 0)
    bulk_endpoint = int(_cfg.get("antagent.hw", "bulk_endpoint"), 0)
    import antagent.hw as hw
    return hw.UsbHardware(id_vendor, id_product, bulk_endpoint)

def create_ant_core():
    import antagent.ant as ant
    return ant.Core(create_hardware())

def create_ant_session():
    import antagent.ant as ant
    session = ant.Session(create_ant_core())
    session.default_read_timeout = int(_cfg.get("antagent.ant", "default_read_timeout"), 0)
    session.default_write_timeout = int(_cfg.get("antagent.ant", "default_write_timeout"), 0)
    session.default_retry = int(_cfg.get("antagent.ant", "default_retry"), 0)
    return session

def create_antfs_host():
    import antagent.antfs as antfs
    keys_file = _cfg.get("antagent.antfs", "auth_pairing_keys")
    keys_file = os.path.expanduser(keys_file)
    keys_dir = os.path.dirname(keys_file)
    if not os.path.exists(keys_dir): os.mkdir(keys_dir)
    keys = dbm.open(keys_file, "c")
    host = antfs.Host(create_ant_session(), keys)
    host.search_network_key = binascii.unhexlify(_cfg.get("antagent.antfs", "search_network_key"))
    host.search_freq = int(_cfg.get("antagent.antfs", "search_freq"), 0)
    host.search_period = int(_cfg.get("antagent.antfs", "search_period"), 0)
    host.search_timeout = int(_cfg.get("antagent.antfs", "search_timeout"), 0)
    host.search_waveform = int(_cfg.get("antagent.antfs", "search_waveform"), 0)
    host.transport_freqs = [int(s, 0) for s in _cfg.get("antagent.antfs", "transport_freq").split(",")]
    host.transport_period = int(_cfg.get("antagent.antfs", "transport_period"), 0)
    host.transport_timeout = int(_cfg.get("antagent.antfs", "transport_timeout"), 0)
    return host

def set_device_sn(sn):
    _cfg.set("antagent", "device_sn", hex(sn))

def get_path(key, file=""):
    path = os.path.expanduser(_cfg.get("antagent", key))
    if not os.path.exists(path): os.mkdir(path)
    return os.path.sep.join([path, file]) if file else path

def get_retry():
    return int(_cfg.get("antagent", "retry"), 0)

# vim: ts=4 sts=4 et
