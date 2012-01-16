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
import time

from gant.ant_core import MessageType, RadioEventType, ChannelEventType, Dispatcher
from gant.ant_workflow import State, Workflow, FINAL_STATE, ERROR_STATE
from gant.ant_command import AsyncCommand

_log = logging.getLogger("gant.ant_dialect")

class SendChannelCommand(State):

    def __init__(self, msg_id, chan_num, *args):
        self.msg_id = msg_id
        self.chan_num = chan_num
        self.args = args

    def enter(self, context, prev_state):
        context.send(self.msg_id, self.chan_num, *self.args)

    def accept(self, context, event):
        if event.source == Dispatcher and event.msg_id == MessageType.CHANNEL_RESPONSE_OR_EVENT:
            (reply_chan_num, reply_msg_id, reply_msg_code) = event.msg_args
            if reply_chan_num == self.chan_num and reply_msg_id == self.msg_id:
                self.result = reply_msg_code
                return self.next_state 


class ResetSystem(State):

    def enter(self, context, prev_state):
        context.send(MessageType.RESET_SYSTEM)
        time.sleep(.25)
        return self.next_state


class SetChannelPeriod(SendChannelCommand):
    
    def __init__(self, chan_num, message_period):
        super(SetChannelPeriod, self).__init__(MessageType.CHANNEL_PERIOD, chan_num, message_period)
        

# vim: et ts=4 sts=4
