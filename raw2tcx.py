#!/usr/bin/python

import sys
import pprint
import logging
import lxml.etree as etree

import antagent.garmin as garmin
import antagent.tcx as tcx

logging.basicConfig(
		level=logging.WARNING,
		out=sys.stderr,
		format="[%(threadName)s]\t%(asctime)s\t%(levelname)s\t%(message)s")

if len(sys.argv) != 2:
	print "usage: %s <file>" % sys.argv[0]
	sys.exit(1)

with open(sys.argv[1]) as file:
	host = garmin.MockHost(file.read())
	device = garmin.Device(host)
	runs = device.get_runs()
	doc = tcx.create_document(garmin.extract_runs(device, runs))
	print etree.tostring(doc, pretty_print=True, xml_declaration=True, encoding="UTF-8")
