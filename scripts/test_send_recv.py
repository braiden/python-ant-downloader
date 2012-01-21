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
import argparse
import struct

import gant
import gant.ant_command as cmds
from gant.ant_core import MessageType

logging.basicConfig(
    level=logging.DEBUG,
    out=sys.stderr,
    format="%(asctime)s %(levelname)s %(message)s")

_log = logging.getLogger()

parser = argparse.ArgumentParser(description="Test Radio commands sending data between two USB ANT sticks.")
parser.add_argument("-m", "--master", action='store_true', help="Run as master.")
parser.add_argument("-s", "--slave", action='store_true', help="Run as slave.")
parser.add_argument("-a", "--ack", action="store_true", help="Communicate with acknowledged messages.")
parser.add_argument("-b", "--burst", action="store_true", help="Communicate with burst messages.")
args = parser.parse_args()
if not args.master and not args.slave:
    parser.print_help()
    sys.exit(1)


class MasterWorkflow(gant.Workflow):

    def __init__(self, chan_num):
        state_set_beacon = MasterWorkflow.SendBeacon(chan_num, "\x00" * 8)
        if args.ack:
            state_wait_for_reply = MasterWorkflow.WaitForAcknowledgedReply(chan_num)
        elif args.burst:
            state_wait_for_reply = MasterWorkflow.WaitForBurstReply(chan_num)
        else:
            state_wait_for_reply = MasterWorkflow.WaitForBroadcastReply(chan_num)
        state_set_beacon.next_state = state_wait_for_reply
        state_wait_for_reply.next_state = state_set_beacon
        super(MasterWorkflow, self).__init__(state_set_beacon)

    class SendBeacon(cmds.SendBroadcast):
        
        def enter(self, ctx):
            self.msg = ctx.result.get('data', self.msg)
            super(MasterWorkflow.SendBeacon, self).enter(ctx)

    class WaitForAcknowledgedReply(cmds.WaitForAcknowledged):
        
        def accept(self, ctx, event):
            result = super(MasterWorkflow.WaitForAcknowledgedReply, self).accept(ctx, event)
            if result:
                ctx.result['data'] = ctx.result[MessageType.ACKNOWLEDGED_DATA][0]
                return self.next_state

    class WaitForBroadcastReply(cmds.WaitForBroadcast):

        def accept(self, ctx, event):
            result = super(MasterWorkflow.WaitForBroadcastReply, self).accept(ctx, event)
            if result:
                ctx.result['data'] = ctx.result[MessageType.BROADCAST_DATA][0]
                return self.next_state

    class WaitForBurstReply(cmds.WaitForBurst):

        def accept(self, ctx, event):
            result = super(MasterWorkflow.WaitForBurstReply, self).accept(ctx, event)
            if result:
                ctx.result['data'] = ctx.result[MessageType.BURST_TRANSFER_PACKET][0]
                return self.next_state


class SlaveWorkflow(gant.Workflow):

    def __init__(self, chan_num):
        state_recv = cmds.WaitForBroadcast(chan_num)
        state_route = SlaveWorkflow.RouteBroadcastData(chan_num)
        state_recv.next_state = state_route
        state_route.next_state = state_recv
        super(SlaveWorkflow, self).__init__(state_recv)

    class RouteBroadcastData(gant.State):

        def __init__(self, chan_num, final_state=gant.FINAL_STATE):
            self.chan_num = chan_num
            self.final_state = final_state
            self.n = 0

        def enter(self, ctx):
            recvd = ctx.result[MessageType.BROADCAST_DATA]
            n = ord(recvd[0]) + 1
            _log.debug("RouteBroadcastData, n=%d", n)
            if n > 255:
                return self.final_state
            else:
                self.n = max(n, self.n)
                if args.ack:
                    state_send = cmds.SendAcknowledged(self.chan_num, chr(self.n) * 8)
                elif args.burst:
                    data = chr(self.n) * 8 + "".join(struct.pack("!Q", x) for x in range(0, 127))
                    state_send = cmds.SendBurst(self.chan_num, data)
                else:
                    state_send = cmds.SendBroadcast(self.chan_num, chr(self.n) * 8)
                state_send.next_state = self.next_state
                return state_send


try:
    dev = gant.GarminAntDevice()
    dev.channels[0].network = dev.networks[0]
    if args.slave:
        workflow = SlaveWorkflow(0)
    elif args.master:
        dev.channels[0].channel_type = 0x10
        workflow = MasterWorkflow(0)
    dev.channels[0].execute(workflow)
finally:
    try: dev.close()
    except: pass
 

# vim: et ts=4 sts=4
