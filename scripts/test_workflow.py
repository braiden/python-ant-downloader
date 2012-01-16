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
	wf = workflow.Workflow(dialect.ResetSystem())
	workflow.execute(disp, wf)
	wf = workflow.Workflow(dialect.SetChannelPeriod(0, 0x1000))
	workflow.execute(disp, wf)
except:
	try: hw.close()
	finally: raise
finally:
	hw.close()
