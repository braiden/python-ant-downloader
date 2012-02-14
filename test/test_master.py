#!/usr/bin/python

import sys
import logging
import time

import antd.ant as ant
import antd.hw as hw

logging.basicConfig(
        level=logging.DEBUG,
        out=sys.stderr,
        format="[%(threadName)s]\t%(asctime)s\t%(levelname)s\t%(message)s")

_LOG = logging.getLogger()

dev = hw.UsbHardware()
core = ant.Core(dev)
session = ant.Session(core)
try:
    channel = session.channels[0]
    network = session.networks[0]
    network.set_key("\x00" * 8)
    channel.assign(channel_type=0x30, network_number=0)
    channel.set_id(device_number=0, device_type_id=0, trans_type=0)
    channel.set_period(0x4000)
    channel.set_search_timeout(20)
    channel.set_rf_freq(40)
    channel.open()
    channel.send_broadcast("testtest")
    while True:
        _LOG.info("READ %s", channel.read(timeout=10))
finally:
    try: session.close()
    except: _LOG.warning("Caught exception while resetting system.", exc_info=True)


# vim: ts=4 sts=4 et
