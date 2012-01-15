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

    result = None

    def __init__(self, message_code):
        self.message_code = message_code

    def on_event(self, context, event):
        if event.type == MessageType and event.msg_id == ANT_RESPONSE:
            (msg_code, msg_status, msg_number) = event.msg_args
            if msg_number == message_number:
                result = ...
                return self

class SetMessagePeriod(AsyncCommmand):
    
    def __init__(self, message_period):
        self.message_period = message_period
        
    def on_event(self, context, event):
        if event.type = CommandStartedEvent:
            contex.send(ANT_MESSAGE_PERIOD, message_period)
            self.wait_for_event = WaitForChannelEvent(ANT_MESSAGE_PERIOD)
            self.add_children(wait_for_event)
            return None
        elif event.source = wait_for_event:
            

# vim: et ts=4 sts=4
