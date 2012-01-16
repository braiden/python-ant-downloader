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
from gant.ant_workflow import State, Workflow, Event, FINAL_STATE, ERROR_STATE
from gant.ant_command import AsyncCommand

_log = logging.getLogger("gant.ant_dialect")

class SendChannelCommandState(State):

    def __init__(self, msg_id, chan_num, next_state, *args):
        self.msg_id = msg_id
        self.chan_num = chan_num
        self.next_state = next_state
        self.args = args

    def enter(self, context, prev_state):
        context.send(self.msg_id, self.chan_num, *self.args)

    def accept(self, context, event):
        if event.source == context.dispatcher and event.msg_id == MessageType.CHANNEL_RESPONSE_OR_EVENT:
            (self.chan_num, self.msg_id, self.msg_code) = event.msg_args
            if self.expected_chan_num == self.chan_num and self.msg_id == self.expected_msg_id:
                return self.next_state 

class ResetSystem(SendRequestMessageState):

    pass

class SetChannelPeriod(SendChannelCommandState):
    
    def __init__(self, chan_num, message_period, next_state=FINAL_STATE):
        SendChannelCommandState.__init__(
                self, MessageType.CHANNEL_PERIOD, chan_num, next_state, message_period)
        

# vim: et ts=4 sts=4
