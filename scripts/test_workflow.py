#!/usr/bin/python

import logging
import sys
import time

import gant.ant_core as core
import gant.ant_workflow as workflow
import gant.ant_usb_hardware as hardware
import gant.ant_command as command

logging.basicConfig(
    level=logging.DEBUG,
    out=sys.stderr,
    format="%(asctime)s %(levelname)s %(message)s")

hw = hardware.UsbHardware(id_vendor=0x0fcf, id_product=0x1008)
try:
    mar = core.Marshaller()
    d = core.Dispatcher(hw, mar)
    executor = workflow.WorkflowExecutor(d)
    executor.execute(command.ResetSystem())
    executor.execute(command.SetNetworkKey(0, "\xa8\xa4\x23\xb9\xf5\x5e\x63\xc1"))
    executor.execute(command.AssignChannel(0, chan_type=0x10, net_num=0))
    executor.execute(command.SetChannelId(0, device_num=0x00, device_type=0x00, trans_type=0x00))
    executor.execute(command.SetChannelPeriod(0, message_period=0x1000))
    executor.execute(command.SetChannelSearchTimeout(0, search_timeout=0xFF))
    executor.execute(command.SetChannelRfFreq(0, rf_freq=0x32))
    executor.execute(command.SetChannelSearchWaveform(0, waveform=0x0053))
    executor.execute(command.OpenChannel(0))
    executor.execute(command.SendBroadcast(0, "TESTTEST"))
    print executor.execute(command.GetDeviceCapabilities()).result
    print executor.execute(command.GetAntVersion()).result
    print executor.execute(command.GetSerialNumber()).result
    print executor.execute(command.GetChannelId(0)).result
    print executor.execute(command.GetChannelStatus(0)).result
    executor.execute(command.CloseChannel(0))
except:
    try: hw.close()
    finally: raise
finally:
    hw.close()

# vim: et ts=4 sts=4
