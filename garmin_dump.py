#!/usr/bin/python

import sys
import pprint

import antagent.garmin as garmin

with open(sys.argv[1]) as file:
	device = garmin.FileDevice(file)
	product_data = device.get_product_data()
	pprint.pprint(product_data)
