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
import os

import antagent.ant as ant
import antagent.antfs as antfs
import antagent.hw as hw
import antagent.garmin as garmin
import antagent.tcx as tcx

Host = antfs.Host
Beacon = antfs.Beacon
Core = ant.Core
Session = ant.Session
Channel = ant.Channel
Network = ant.Network
Device = garmin.Device

AntError = ant.AntError
AntTimeoutError = ant.AntTimeoutError
AntTxFailedError = ant.AntTxFailedError
AntChannelClosedError = ant.AntChannelClosedError
DeviceNotSupportedError = garmin.DeviceNotSupportedError

__all__ = [
    "UsbAntFsHost",
    "Host",
    "Beacon",
    "Core",
    "Session",
    "Channel",
    "Network",
    "Device",
    "AntError",
    "AntTimeoutError",
    "AntTxFailedError",
    "AntChannelClosedError",
    "DeviceNotSupportedError",
]

_log = logging.getLogger("antagent")

def UsbAntFsHost(known_devices):
    """
    Create a new new Ant FS Host (client)
    using default implmentation of ANT api
    and usb hardware connection.
    """
    try:
        usb = hw.UsbHardware()
        core = ant.Core(usb)
        session = ant.Session(core)
        host = antfs.Host(session, known_devices)
        return host
    except Exception as e:
        try:
            if host: host.close()
            elif session: session.close()
        except Exception:
            _log("Caught exception while cleaning up resources.", exc_info=True)
        finally:
            raise e
            

# vim: ts=4 sts=4 et
