# Copyright (c) 2012, Braiden Kindt.
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without modification,
# are permitted provided that the following conditions are met:
# 
#    1. Redistributions of source code must retain the above copyright notice,
#       this list of conditions and the following disclaimer.
# 
#    2. Redistributions in binary form must reproduce the above copyright notice,
#       this list of conditions and the following disclaimer in the documentation
#       and/or other materials provided with the distribution.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDER AND CONTRIBUTORS ''AS IS'' AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR
# ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
# ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from gant.ant_api import Device, Channel, Network, AntError
from gant.ant_workflow import Workflow, State, WorkflowError, StateExecutionError, StateTransitionError

__all__ = [
    "GarminAntDevice",
    "Device",
    "Channel",
    "Network",
    "AntError",
    "Workflow",
    "State",
    "WorkflowError",
    "StateExecutionError",
    "StateTransitionError",
]

def GarminAntDevice():
    """
    Create a new ANT Device configured for
    use with a Garmin USB ANT Stick (nRF24AP2-USB).
    http://search.digikey.com/us/en/products/ANTUSB2-ANT/1094-1002-ND/2748492
    """
    from gant.ant_usb_hardware import UsbHardware
    from gant.ant_core import Dispatcher, Marshaller
    from gant.ant_workflow import WorkflowExecutor
    import gant.ant_command as commands
    hardware = None
    dispatcher = None
    executor = None
    device = None
    try:
        hardware = UsbHardware(id_vendor=0x0fcf, id_product=0x1008)
        dispatcher = Dispatcher(hardware, Marshaller())
        executor = WorkflowExecutor(dispatcher)
        device = Device(executor, commands)
        return device
    except:
        try:
            if device: device.close()
            elif dispatcher: dispatcher.close()
            elif executor: executor.close()
            elif hardware: hardware.close()
        finally: raise


# vim: et ts=4 sts=4
