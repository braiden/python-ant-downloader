#!/usr/bin/python

import logging
import sys

import antagent.ant as ant
import antagent.antfs as antfs
import antagent.hw as hw

logging.basicConfig(
        level=logging.DEBUG,
        out=sys.stderr,
        format="[%(threadName)s]\t%(asctime)s\t%(levelname)s\t%(message)s")

usb = hw.UsbHardware()
core = ant.Core(usb)
session = ant.Session(core)
host = antfs.Host(session)

try:
    host.search()
    host.link()
    host.auth()
finally:
    session.close()

# vim: ts=4 sts=4 et
