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

import logging

from gant.ant_core import MessageType, RadioEventType, ChannelEventType
from gant.ant_command import AsyncCommand

_log = logging.getLogger("gant.ant_dialect")

class WaitForChannelEvent(AsyncCommand):

    def __init__(self, msg_id, chan_number):
        self.source = self
        self.expected_chan_number = chan_number
        self.expected_msg_id = msg_id

    def on_event(self, context, event):
        if event.source == context.dispatcher and event.msg_id = MessageType.CHANNEL_RESPONSE_OR_EVENT:
            (self.chan_number, self.msg_id, self.msg_code) = event.msg_args
            if self.expected_chan_number == self.chan_number and self.msg_id == self.expected_msg_id:
                self.done = True
                return self
        return event


class ChannelCommand(AsyncCommand):

    def __init__(self, message_type, chan_number, *args):
        self.message_type = message_type
        self.chan_number = chan_number
        self.args = args

    def on_event(self, context, event):
        if event.source == self:
            context.send(self.message_type, self.chan_number, *self.args)
            self.wait = WaitForChannelEvent(self.message_type, self.chan_number)
            context.add_command(self.wait)
        elif event.source == self.wait:
            self.result = event.source.msg_code
            self.done = True
            return self
        return event


class SetMessagePeriod(ChannelCommmand):
    
    def __init__(self, chan_number, message_period):
        super(SetMessagePeriod, self).__init__(MessagType.CHANNEL_PERIOD, chan_number, message_period)
        

# vim: et ts=4 sts=4
