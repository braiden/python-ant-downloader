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
import time

from gant.ant_api import AntError
from gant.ant_core import MessageType, RadioEventType, ChannelEventType, Dispatcher, value_of
from gant.ant_workflow import State, Workflow, FINAL_STATE, chain

_log = logging.getLogger("gant.ant_dialect")


def is_ant_event(event, msg_id, chan_num=-1):
    return (event.source == Dispatcher and event.msg_id == msg_id
        and (chan_num < 0 or (event.msg_args[0] and 0x1f) == chan_num))


class SendChannelCommand(State):

    def __init__(self, msg_id, chan_num, *args):
        self.msg_id = msg_id
        self.chan_num = chan_num
        self.args = args

    def enter(self, context):
        context.send(self.msg_id, self.chan_num, *self.args)

    def accept(self, context, event):
        if is_ant_event(event, MessageType.CHANNEL_RESPONSE_OR_EVENT, self.chan_num):
            (reply_chan_num, reply_msg_id, reply_msg_code) = event.msg_args
            if reply_msg_id == self.msg_id:
                context.result[self.msg_id] = reply_msg_code
                if reply_msg_code:
                    raise AntError(
                            "Non-zero reply (0x%x) to ANT_%s"
                                    % (reply_msg_code, value_of(MessageType, reply_msg_id)),
                            AntError.ERR_MSG_FAILED) 
                else:
                    return self.next_state 


class RequestMessage(State):
    
    def __init__(self, msg_id, chan_num=-1):
        self.msg_id = msg_id
        self.chan_num = chan_num

    def enter(self, context):
        context.send(MessageType.REQUEST_MESSAGE, max(0, self.chan_num), self.msg_id)

    def accept(self, context, event):
        if is_ant_event(event, self.msg_id, self.chan_num):
                context.result[self.msg_id] = event.msg_args
                return self.next_state


class WaitForRfEvent(State):

    def __init__(self, chan_num, event_id):
        self.chan_num = chan_num
        self.event_id = event_id

    def accept(self, context, event):
        if is_ant_event(event, MessageType.CHANNEL_RESPONSE_OR_EVENT, self.chan_num):
            (reply_chan_num, reply_msg_id, reply_msg_code) = event.msg_args
            if reply_msg_id == 1 and reply_msg_code == self.event_id:
                return self.next_state 


class ResetSystem(RequestMessage):

    def __init__(self):
        super(ResetSystem, self).__init__(MessageType.STARTUP_MESSAGE)

    def enter(self, context):
        context.send(MessageType.RESET_SYSTEM)
        

class UnassignChannel(SendChannelCommand):

    def __init__(self, chan_num):
        super(UnassignChannel, self).__init__(MessageType.UNASSIGN_CHANNEL, chan_num)


class AssignChannel(SendChannelCommand):

    def __init__(self, chan_num, chan_type, net_num):
        super(AssignChannel, self).__init__(MessageType.ASSIGN_CHANNEL, chan_num, chan_type, net_num)


class SetChannelId(SendChannelCommand):

    def __init__(self, chan_num, device_num, device_type, trans_type):
        super(SetChannelId, self).__init__(
                MessageType.CHANNEL_ID, chan_num, device_num, device_type, trans_type)


class SetChannelPeriod(SendChannelCommand):

    def __init__(self, chan_num, message_period):
        super(SetChannelPeriod, self).__init__(MessageType.CHANNEL_PERIOD, chan_num, message_period)


class SetChannelSearchTimeout(SendChannelCommand):

    def __init__(self, chan_num, search_timeout):
        super(SetChannelSearchTimeout, self).__init__(
                MessageType.CHANNEL_SEARCH_TIMEOUT, chan_num, search_timeout)


class SetChannelRfFreq(SendChannelCommand):

    def __init__(self, chan_num, rf_freq):
        super(SetChannelRfFreq, self).__init__(MessageType.CHANNEL_RF_FREQ, chan_num, rf_freq)


class SetNetworkKey(SendChannelCommand):

    def __init__(self, net_num, key):
        super(SetNetworkKey, self).__init__(MessageType.NETWORK_KEY, net_num, key)


class OpenChannel(SendChannelCommand):
    
    def __init__(self, chan_num):
        super(OpenChannel, self).__init__(MessageType.OPEN_CHANNEL, chan_num)


class CloseChannel(Workflow):

    def __init__(self, chan_num):

        initial_state = chain(
                SendChannelCommand(MessageType.CLOSE_CHANNEL, chan_num),
                WaitForRfEvent(chan_num, RadioEventType.CHANNEL_CLOSED))
        super(CloseChannel, self).__init__(initial_state)


class OpenRxScanMode(SendChannelCommand):

    def __init__(self):
        super(OpenRxScanMode, self).__init__(MessageType.OPEN_RX_SCAN_MODE)


class SetChannelSearchWaveform(SendChannelCommand):

    def __init__(self, chan_num, waveform):
        super(SetChannelSearchWaveform, self).__init__(
                MessageType.SEARCH_WAVEFORM, chan_num, waveform)


class GetDeviceCapabilities(RequestMessage):

    def __init__(self):
        super(GetDeviceCapabilities, self).__init__(MessageType.CAPABILITIES)

    def accept(self, context, event):
        result = super(GetDeviceCapabilities, self).accept(context, event)
        if result is self.next_state:
            context.result.update(dict(zip(
                ['max_channels', 'max_networks', 'standard_options',
                 'advanced_options_1', 'advanced_options_2', 'reserved'],
                context.result[MessageType.CAPABILITIES])))
        return result


class GetAntVersion(RequestMessage):

    def __init__(self):
        super(GetAntVersion, self).__init__(MessageType.VERSION)


class GetSerialNumber(RequestMessage):
    
    def __init__(self):
        super(GetSerialNumber, self).__init__(MessageType.SERIAL_NUMBER)


class GetChannelId(RequestMessage):

    def __init__(self, chan_num):
        super(GetChannelId, self).__init__(MessageType.CHANNEL_ID, chan_num)

    def accept(self, context, event):
        result = super(GetChannelId, self).accept(context, event)
        if result is self.next_state:
            context.result.update(dict(zip(
                ['chan_num', 'device_num', 'device_type', 'man_id'],
                context.result[MessageType.CHANNEL_ID])))
        return result
    

class GetChannelStatus(RequestMessage):

    def __init__(self, chan_num):
        super(GetChannelStatus, self).__init__(MessageType.CHANNEL_STATUS, chan_num)

    def accept(self, context, event):
        result = super(GetChannelStatus, self).accept(context, event)
        if result is self.next_state:
            context.result.update(dict(zip(
                ['chan_num', 'chan_state'],
                context.result[MessageType.CHANNEL_STATUS])))
        return result


class SendBroadcast(WaitForRfEvent):

    def __init__(self, chan_num, msg):
        super(SendBroadcast, self).__init__(chan_num, RadioEventType.TX)
        self.msg = msg

    def enter(self, ctx):
        ctx.send(MessageType.BROADCAST_DATA, self.chan_num, self.msg)


class WaitForBroadcast(State):

    def __init__(self, chan_num):
        self.chan_num = chan_num

    def accept(self, ctx, event):
        if is_ant_event(event, MessageType.BROADCAST_DATA, self.chan_num):
            ctx.result[MessageType.BROADCAST_DATA] = event.msg_args[1]
            return self.next_state


class SendAcknowledged(State):

    def __init__(self, chan_num, msg):
        self.chan_num = chan_num
        self.msg = msg

    def enter(self, ctx):
        ctx.send(MessageType.ACKNOWLEDGED_DATA, self.chan_num, self.msg)

    def accept(self, ctx, event):
        if is_ant_event(event, MessageType.CHANNEL_RESPONSE_OR_EVENT, self.chan_num):
            (result_chan_num, result_message_id, result_message_code) = event.msg_args
            if result_message_id == 1:
                if result_message_code == RadioEventType.TRANSFER_TX_COMPLETED:
                    return self.next_state
                else:
                    raise AntError(
                        "Acknowledged Transfer Failed (channel=%d). %s"
                                % (self.chan_num, value_of(RadioEventType, result_message_code)),
                        AntError.ERR_MSG_FAILED)
        

class WaitForAcknowledged(State):

    def __init__(self, chan_num):
        self.chan_num = chan_num

    def accept(self, ctx, event):
        if is_ant_event(event, MessageType.ACKNOWLEDGED_DATA, self.chan_num):
            ctx.result[MessageType.ACKNOWLEDGED_DATA] = event.msg_args[1]
            return self.next_state


class WaitForBurst(State):
    
    def __init__(self, chan_num):
        self.chan_num = chan_num

    def enter(self, ctx):
       ctx.result[MessageType.BURST_TRANSFER_PACKET] = ""

    def accept(self, ctx, event):
        if is_ant_event(event, MessageType.BURST_TRANSFER_PACKET, self.chan_num):
            ctx.result[MessageType.BURST_TRANSFER_PACKET] += event.msg_args[1]
        elif is_ant_event(event, MessageType.CHANNEL_RESPONSE_OR_EVENT, self.chan_num):
            (result_chan_num, result_message_id, result_message_code) = event.msg_args
            if result_message_id == 1:
                if result_message_code == RadioEventType.TX and ctx.result[MessageType.BURST_TRANSFER_PACKET]:
                    return self.next_state
                elif result_message_code == RadioEventType.TX:
                    pass
                else:
                    raise AntError(
                        "Burst Transfer Aborted (channel=%d). %s"
                                % (self.chan_num, value_of(RadioEventType, result_message_code)),
                        AntError.ERR_MSG_FAILED)


class SendBurst(Workflow):

    def __init__(self, chan_num, msg):
        self.chan_num = chan_num
        self.msg = msg
        self.offset = 0
        self.seq_num = 0
        s1 = SendBurst.PrimeData(n=4)
        s2 = WaitForRfEvent(self.chan_num, RadioEventType.TRANSFER_TX_START)
        s3 = SendBurst.SendBurstPackets()
        s4 = WaitForRfEvent(self.chan_num, RadioEventType.TRANSFER_TX_COMPLETED)
        super(SendBurst, self).__init__(chain(s1, s2, s3, s4))

    def send_next_packet(self, ctx):
        if self.offset < len(self.msg):
            data = self.msg[self.offset:self.offset + 8]
            chan_num = ((self.seq_num << 5) | self.chan_num) & 0x7F
            chan_num |= 0x80 if self.offset + 8 >= len(self.msg) else 0
            if ctx.send(MessageType.BURST_TRANSFER_PACKET, chan_num, data):
                self.offset += 8
                self.seq_num += 1
            return True

    def accept(self, ctx, event):
        if is_ant_event(event, MessageType.CHANNEL_RESPONSE_OR_EVENT, self.chan_num):
            (result_chan_num, result_message_id, result_message_code) = event.msg_args
            if result_message_id == 1 and not (
                        result_message_code == RadioEventType.TRANSFER_TX_COMPLETED
                        or result_message_code == RadioEventType.TRANSFER_TX_START):
                    raise AntError(
                        "Burst Transfer Failed (channel=%d). %s"
                                % (self.chan_num, value_of(RadioEventType, result_message_code)),
                        AntError.ERR_MSG_FAILED)
        return super(SendBurst, self).accept(ctx, event) 

    class PrimeData(State):
        # FIXME, i can miss TRANSFER_TX_START if received
        # while priming output buffer. Maybe not an issue?
        # just make sure prime data starts imediately after
        # a beacon.

        def __init__(self, n):
            self.n = n

        def enter(self, ctx):
            for n in range(0, self.n):
                ctx.workflow.send_next_packet(ctx)
            return self.next_state

    class SendBurstPackets(State):

        def enter(self, ctx):
            while ctx.workflow.send_next_packet(ctx):
                pass
            return self.next_state


# vim: et ts=4 sts=4
