#!/usr/bin/python

import logging
import sys
import time
import argparse

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
args = parser.parse_args()
if not args.master and not args.slave:
    parser.print_help()
    sys.exit(1)


class MasterWorkflow(gant.Workflow):

    def __init__(self, chan_num):
        state_set_beacon = MasterWorkflow.SendBeacon(chan_num, "\x00" * 8)
        state_wait_for_reply = cmds.WaitForBroadcast(chan_num)
        state_set_beacon.next_state = state_wait_for_reply
        state_wait_for_reply.next_state = state_set_beacon
        super(MasterWorkflow, self).__init__(state_set_beacon)

    class SendBeacon(cmds.SendBroadcast):
        
        def enter(self, ctx):
            self.msg = ctx.result.get(MessageType.BROADCAST_DATA, self.msg)
            super(MasterWorkflow.SendBeacon, self).enter(ctx)

    class WaitForReply(cmds.WaitForBroadcast):

        def accept(self, ctx, event):
            result = super(MasterWorkflow.WaitForReply, self).accept(ctx, event)
            if result and ctx.result[MessageType.BROADCAST_DATA][0] == "\xff":
                return FINAL_STATE
            else:
                return result

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
    dev.close()
 

# vim: et ts=4 sts=4
