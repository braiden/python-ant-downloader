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
import pkg_resources
import logging

_log = logging.getLogger("antd.cfg")
_cfg = ConfigParser.SafeConfigParser()

CONFIG_FILE_VERSION = 1
DEFAULT_CONFIG_LOCATION = os.path.expanduser("~/.antd/antd.cfg")

def write_default_config(target):
    dirname = os.path.dirname(target)
    if not os.path.exists(dirname): os.makedirs(dirname)
    with open(target, "w") as file:
        file.write(pkg_resources.resource_string(__name__, "antd.cfg"))
    
def read(file=None):
    if file is None:
        file = DEFAULT_CONFIG_LOCATION
        if not os.path.isfile(file):
            # copy the template configuration file to users .antd directory
            write_default_config(file)
    read = _cfg.read([file])
    if read:
        # config file read sucessfuelly, setup logger
        _log.setLevel(logging.WARNING)
        init_loggers()
        # check for version mismatch
        try: version = _cfg.getint("antd", "version")
        except (ConfigParser.NoOptionError, ConfigParser.NoSectionError): version = -1
        if version != CONFIG_FILE_VERSION:
            new_file = DEFAULT_CONFIG_LOCATION + ".%d" % CONFIG_FILE_VERSION
            write_default_config(new_file)
            _log.warning("Config file version does not match expected version (%d).", CONFIG_FILE_VERSION)
            _log.warning("If you have issues recommended you replace your configuration with %s", new_file)  
            _log.warning("Set [antd] version=%d in your current config file to disable this warning.", CONFIG_FILE_VERSION)
    return read

def init_loggers(force_level=None, out=sys.stdin):
    level = force_level if force_level is not None else logging.ERROR
    logging.basicConfig(
            level=level,
            out=out,
            format="[%(threadName)s]\t%(asctime)s\t%(levelname)s\t%(message)s")
    try:
        for logger, log_level in _cfg.items("antd.logging"):
            level = force_level if force_level is not None else logging.getLevelName(log_level)
            logging.getLogger(logger).setLevel(level) 
    except ConfigParser.NoSectionError:
        pass

def create_hardware():
    id_vendor = int(_cfg.get("antd.hw", "id_vendor"), 0)
    id_product = int(_cfg.get("antd.hw", "id_product"), 0)
    bulk_endpoint = int(_cfg.get("antd.hw", "bulk_endpoint"), 0)
    import antd.hw as hw
    return hw.UsbHardware(id_vendor, id_product, bulk_endpoint)

def create_ant_core():
    import antd.ant as ant
    return ant.Core(create_hardware())

def create_ant_session():
    import antd.ant as ant
    session = ant.Session(create_ant_core())
    session.default_read_timeout = int(_cfg.get("antd.ant", "default_read_timeout"), 0)
    session.default_write_timeout = int(_cfg.get("antd.ant", "default_write_timeout"), 0)
    session.default_retry = int(_cfg.get("antd.ant", "default_retry"), 0)
    return session

def create_antfs_host():
    import antd.antfs as antfs
    keys_file = _cfg.get("antd.antfs", "auth_pairing_keys")
    keys_file = os.path.expanduser(keys_file)
    keys_dir = os.path.dirname(keys_file)
    if not os.path.exists(keys_dir): os.makedirs(keys_dir)
    keys = antfs.KnownDeviceDb(keys_file)
    host = antfs.Host(create_ant_session(), keys)
    host.search_network_key = binascii.unhexlify(_cfg.get("antd.antfs", "search_network_key"))
    host.search_freq = int(_cfg.get("antd.antfs", "search_freq"), 0)
    host.search_period = int(_cfg.get("antd.antfs", "search_period"), 0)
    host.search_timeout = int(_cfg.get("antd.antfs", "search_timeout"), 0)
    host.search_waveform = int(_cfg.get("antd.antfs", "search_waveform"), 0)
    host.transport_freqs = [int(s, 0) for s in _cfg.get("antd.antfs", "transport_freq").split(",")]
    host.transport_period = int(_cfg.get("antd.antfs", "transport_period"), 0)
    host.transport_timeout = int(_cfg.get("antd.antfs", "transport_timeout"), 0)
    return host

def create_garmin_connect_plugin():
    if _cfg.getboolean("antd.connect", "enabled"):
        import antd.connect as connect
        client = connect.GarminConnect()
        client.username = _cfg.get("antd.connect", "username")
        client.password = _cfg.get("antd.connect", "password")
        try:
            client.cache = os.path.expanduser(_cfg.get("antd.connect", "cache")) 
        except ConfigParser.NoOptionError: pass
        return client 

def create_tcx_plugin():
    if _cfg.getboolean("antd.tcx", "enabled"):
        import antd.tcx as tcx
        tcx = tcx.TcxPlugin()
        tcx.tcx_output_dir = os.path.expanduser(_cfg.get("antd.tcx", "tcx_output_dir"))
        try:
            tcx.cache = os.path.expanduser(_cfg.get("antd.tcx", "cache")) 
        except ConfigParser.NoOptionError: pass
        return tcx

def get_path(section, key, file="", tokens={}):
    path = os.path.expanduser(_cfg.get(section, key))
    path = path % tokens
    if not os.path.exists(path): os.makedirs(path)
    return os.path.sep.join([path, file]) if file else path

def get_retry():
    return int(_cfg.get("antd", "retry"), 0)

def get_raw_output_dir():
    return get_path("antd", "raw_output_dir")


# vim: ts=4 sts=4 et
