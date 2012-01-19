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
import sys

from gant.ant_core import MessageType, RadioEventType, ChannelEventType, Listener, Dispatcher, value_of

_log = logging.getLogger("gant.ant_workflow")

def chain(*states):
    for (s1, s2) in zip(states[:-1], states[1:]):
        s1.next_state = s2
    return states[0] 


class Event(object):

    source = None

    def __init__(self, name=None):
        if name: self.name = name

    def __str__(self):
        try: return self.name
        except AttributeError: return self.__class__.__name__


class WorkflowExecutor(Listener):

    def __init__(self, dispatcher):
        self.dispatcher = dispatcher

    def execute(self, state):
        self.ctx = Context(self.dispatcher, None)
        self.workflow = Workflow(state)
        if self.workflow.enter(self.ctx) != FINAL_STATE:
            self.dispatcher.loop(self)
        return self.ctx

    def on_message(self, dispatcher, message):
        (msg_id, msg_args) = message
        event = Event("ANT_%s%s" % (value_of(MessageType, msg_id), msg_args))
        event.source = Dispatcher
        event.msg_id = msg_id
        event.msg_args = msg_args
        state = self.workflow.accept(self.ctx, event)
        if state != FINAL_STATE:
            return True

    def close(self):
        self.dispatcher.close()


class State(object):

    next_state = None

    def __init__(self, name=None):
        if name: self.name = name

    def enter(self, context):
        pass

    def accept(self, context, event):
        return self.next_state

    def __str__(self):
        try: return self.name
        except AttributeError: return self.__class__.__name__

FINAL_STATE = State("FINAL_STATE")
INITIAL_STATE = State("INITIAL_STATE")
State.next_state = FINAL_STATE


class Context(object):
    
    def __init__(self, parent_context, workflow):
        self.parent_context = parent_context
        self.workflow = workflow
        self.result = {}

    def send(self, msg_id, *args):
        self.parent_context.send(msg_id, *args)

    def __str__(self):
        if self.workflow:
            parent_str = str(self.parent_context)
            self_str = str(self.workflow)
            return parent_str + "/" + self_str if parent_str else self_str
        else:
            return ""


class Workflow(State):

    def __init__(self, initial_state):
        self.initial_state = initial_state
        self.state = INITIAL_STATE

    def enter(self, context):
        self.context = Context(context, self)
        _log.debug("%s START: %s", self.context, self.initial_state)
        return self.transition(self.context, self.initial_state)

    def accept(self, context, event):
        try:
            _log.debug("%s EVENT: %s", self.context, event)
            return self.transition(self.context, self.state.accept(self.context, event))
        except Exception as e:
            raise StateExecutionError, StateExecutionError(e, self.state), sys.exc_traceback
    
    def transition(self, context, state):
        while state is not None:
            _log.debug("%s TRANSITION: %s => %s", self.context, self.state, state)
            self.state = state
            try:
                state = state.enter(self.context)
            except Exception as e:
                raise StateTransitionError, StateTransitionError(e, self.state, state), sys.exc_traceback
        if self.state is FINAL_STATE:
            self.context.parent_context.result.update(self.context.result)
            return self.next_state


class WorkflowError(Exception):
    pass
class StateExecutionError(WorkflowError):
    pass
class StateTransitionError(WorkflowError):
    pass


# vim: et ts=4 sts=4
