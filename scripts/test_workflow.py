#!/usr/bin/python

import logging
import sys

import gant.ant_core as core
import gant.ant_workflow as workflow
import gant.ant_usb_hardware as hardware
import gant.ant_dialect as dialect

logging.basicConfig(
	level=logging.DEBUG,
	out=sys.stderr,
	format="%(asctime)s %(levelname)s %(message)s")

hw = hardware.UsbHardware(id_vendor=0x0fcf, id_product=0x1008)
try:
	mar = core.Marshaller()
	disp = core.Dispatcher(hw, mar)
	workflow.execute(disp, dialect.ResetSystem())
	workflow.execute(disp, dialect.SetChannelPeriod(0, 0x1000))
	cap = workflow.execute(disp, dialect.GetDeviceCapabilities())
	print cap
	print cap.max_networks, cap.max_channels
except:
	try: hw.close()
	finally: raise
finally:
	hw.close()
