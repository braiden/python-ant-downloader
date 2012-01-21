#!/usr/bin/python

# Copyright (c) 2012, Braiden Kindt.
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
# 
#   1. Redistributions of source code must retain the above copyright
#      notice, this list of conditions and the following disclaimer.
# 
#   2. Redistributions in binary form must reproduce the above
#      copyright notice, this list of conditions and the following
#      disclaimer in the documentation and/or other materials
#      provided with the distribution.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDER AND CONTRIBUTORS
# ''AS IS'' AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY
# WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

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
