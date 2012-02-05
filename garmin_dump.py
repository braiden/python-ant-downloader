#!/usr/bin/python

import sys

import antagent.garmin as garmin

with open(sys.argv[1]) as file:
	device_caps = garmin.A000(garmin.file_reader, file)
	runs = garmin.A1000(garmin.file_reader, file)
	for pkt in device_caps: print pkt
	for typ in runs:
		for pkt in typ: print pkt

