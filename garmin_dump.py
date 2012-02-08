#!/usr/bin/python

import sys
import pprint
import logging

import antagent.garmin as garmin

logging.basicConfig(
		level=logging.DEBUG,
		out=sys.stderr,
		format="[%(threadName)s]\t%(asctime)s\t%(levelname)s\t%(message)s")

if len(sys.argv) != 2:
	print "usage: %s <file>" % sys.argv[0]
	sys.exit(1)

with open(sys.argv[1]) as file:
	host = garmin.MockHost(file.read())
	device = garmin.Device(host)
	pprint.pprint(device.get_runs())
