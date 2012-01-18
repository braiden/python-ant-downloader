#!/usr/bin/python

import logging
import sys
import time

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
	d = core.Dispatcher(hw, mar)
	workflow.execute(d, dialect.ResetSystem())
	d.drain()
	try:
		workflow.execute(d, dialect.SetNetworkKey(0, "\xa8\xa4\x23\xb9\xf5\x5e\x63\xc1"))
		workflow.execute(d, dialect.AssignChannel(0, chan_type=0x00, net_num=0))
		workflow.execute(d, dialect.SetChannelId(0, device_num=0x00, device_type=0x00, trans_type=0x00))
		workflow.execute(d, dialect.SetChannelPeriod(0, message_period=0x1000))
		workflow.execute(d, dialect.SetChannelSearchTimeout(0, search_timeout=0xFF))
		workflow.execute(d, dialect.SetChannelRfFreq(0, rf_freq=0x32))
		workflow.execute(d, dialect.SetChannelSearchWaveform(0, waveform=0x0053))
		workflow.execute(d, dialect.OpenChannel(0))
		print workflow.execute(d, dialect.GetDeviceCapabilities()).result
		print workflow.execute(d, dialect.GetAntVersion()).result
		print workflow.execute(d, dialect.GetSerialNumber()).result
		print workflow.execute(d, dialect.GetChannelId(0)).result
		print workflow.execute(d, dialect.GetChannelStatus(0)).result
		workflow.execute(d, dialect.CloseChannel(0))
	finally:
		d.drain()
except:
	try: hw.close()
	finally: raise
finally:
	hw.close()
