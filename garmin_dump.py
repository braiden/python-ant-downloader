#!/usr/bin/python

import sys

import antagent.garmin as garmin

with open(sys.argv[1]) as f:
	for pkt in garmin.read(f):
		print pkt
