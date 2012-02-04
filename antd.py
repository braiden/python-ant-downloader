#!/usr/bin/python

import logging
import sys

import antagent

logging.basicConfig(
        level=logging.DEBUG,
        out=sys.stderr,
        format="[%(threadName)s]\t%(asctime)s\t%(levelname)s\t%(message)s")

host = antagent.AntHost()

try:
    host.search()
    host.link()
    host.auth()
finally:
    host.close()

# vim: ts=4 sts=4 et
