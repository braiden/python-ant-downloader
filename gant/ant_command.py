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
import collections

from gant.ant_core import Listener, MessageType, RfEventType, ChannelEventType

_log = logging.getLogger("gant.ant_command")

class AsyncCommandListener(Listener):
    """
    Decorate the given AsynCommand to support
    on_message dispatcher api (so that an AsyncCommand
    can be registered with Dispatcher.)
    """
    
    def __init__(self, async_command):
        self.async_command = async_command

    def on_message(self, dispatcher, msg):
        event = AntMessageEvent(*msg)
        context = AsyncCommandContext(dispatcher)
        self.async_command.on_event(context, event)
        return None if self.async_command.done else True 
    
    def __getattr__(self, attrib):
        """
        Delegate to the decorated async command.
        """
        return getattr(self.async_command, attrib)


class Event(object):
    """
    Base class for events created by dispatcher,
    or child Async commands.
    """

    type = None
    msg_id = None

    def __init__(self, type, msg_id):
        self.type = type
        self.msg_id = msg_id


class AntMessageEvent(Event):
    """
    Lowest level event, containing the ANT
    msg_id an any arguments as unpacked by marshaller.
    """
   
    type = MessageType
    msg_id = None
    msg_args = None

    def __init__(self, msg_id, msg_args):
        self.msg_id = msg_id
        self.msg_args = msg_args


class AsyncCommand(object):
    """
    State machine which will receive callbacks
    for each ant message. Context provides means
    of sending message, or building more advanced
    commands by filtering through other AsyncCommand
    """
    
    """
    Command's should update this flag to indicate
    the workflow as reached terminal state and:
    Tf they are a memember of composite, they should
    be removed. If they are a root of loop() loop
    should terminated.
    """
    done = False

    def __init__(self):
        self.dispatcher = dispatcher

    def on_event(self, context, event):
        """
        Handle the given event. Typically command should: Return
        None to stop event propgation it if can handle it. Return
        event as-is to continue propgation of unsupported event
        types. on_event may also return an array of events if ANT
        message results in more than one application level event.
        """
        pass


class AsyncCommandContext(object):

    def __init__(self, dispatcher):
        self.dispatcher = dispatcher

    def send(self, msg_id, *msg_args):
        """
        Delegate to Dispatcher.send
        """
        self.dispatcher.send(msg_id, *msg_args)


class TreeAsyncCommand(AsyncCommand):
    """
    An Async Command which delegates to higher level commands.
    AsyncCommands can be built in a hierachial fashion
    with the root command build on top of other command
    which provide a translation. e.g. an AsyncDeviceSetupCommand
    can invoke AsyncAssignChannelId command. AntFsCommand
    can invoke AntFsFindBeaconCommand... see ant_commands
    """

    """
    Decorate the given async command to support
    composition. The compsition methods (e.g add_command) will be
    availble in the context passed during invokation of the wrapped cmd
    and on the returned wrapper.
    """
    def __init__(self, async_command, parent=None):
        self.async_command = async_command
        self.children = []
        self.parent = parent

    def on_event(self, context, event):
        """
        Dispatcher the given event to any children of async
        command managed by this instance. The distinct results
        from the children are all passed into the async manged
        by this instance.
        """
        # the resulted results must be unique'd
        results = set()
        # collect all events what need to be dispatched
        events = []
        for child in list(self.children):
            # invoke the child command (possibly recursively)
            child_events = child.on_event(context, event)
            if child.done:
                # child is done, remove from pool
                self.remove_command(child)
            try:
                events.extend(child_events)
            except TypeError:
                events.append(child_events)
        # collect all events dispatch to parent
        try:
            events.extend(event)
        except TypeError:
            events.append(event)
        # dispatch events to the command wrapped by this
        events_seen = set()
        for event in events: 
            if not event in events_seen:
                events_seen.add(event)
                command_called = True
                # invoke this command with each of the child results
                ctx = TreeAsyncCommandContext(context, self)
                result = self.async_command.on_event(ctx, event)
                if result: results.add(result)
                if self.done:
                    break
        return results
            
    def add_command(self, async_command):
        """
        Add A command to execute before the one currently being managed.
        The command can dispatch its own event types to the parent, or filter
        and messages.
        """
        cmd = TreeAsyncCommand(async_command, self)
        self.children.append(cmd)

    def remove_command(self, async_command):
        """
        Remove the given command from this parent.
        """
        try:
            self.children.remove(async_command)
        except ValueError:
            self.children = [c for c in self.children if c.async_command != async_command]

    def __getattr__(self, attrib):
        """
        Delegate to the decorated async command.
        """
        return getattr(self.async_command, attrib)

    @property
    def done(self):
        return self.async_command.done

    @done.setter
    def done(self, value):
        self.async_command.done = value


class TreeAsyncCommandContext(AsyncCommandContext):
    """
    The AsyncCommandExecutionConetxt is passed into commands.
    It provides access to send data over ant as well as manages
    it's child commands.
    """

    EVENT_COMMAND_ADDED = 1

    def __init__(self, context, listener):
        self.context = context
        self.listener = listener

    def send(self, msg_id, *msg_args):
        self.context.send(msg_id, *msg_args)

    def add_command(self, async_command):
        """
        Delegate to AsyncCommandExecutionListener.add_command
        """
        self.listener.add_command(async_command)
        ctx = CompoostiteAsyncCommandContext(self.context, self.listener)
        async_command.on_event(ctx, Event(
                TreeAsyncCommandContext,
                TreeAsyncCommandContext.EVENT_COMMAND_ADDED))

    def remove_command(self, async_command):
        """
        Delegate to AsyncCommandExecutionListener.remove_command
        """
        self.listener.remove_command(async_command)
        

class LoggingAsyncCommand(AsyncCommand):
    """
    Default implemenation for a Root AsyncCommand.
    Any Messages which are not filtered (processed)
    by a child AsyncCommand are logged to debug.
    """

    def on_event(self, context, event):
        if event.type == MessageType:
            msg_id = event.msg_id
            if msg_id != MessageType.CHANNEL_RESPONSE_OR_EVENT:
                msg_name = value_of(MessageType, msg_id) or msg_id
                _log.debug("Unhandled Reply %s: %s" % (msg_name, event.msg_args))
            else:
                event_name = value_of(RfEventType, msg_id) or value_of(ChannelEventType, msg_id) or msg_id
                _log.debug("Unhandled Event %s: %s" % (event_name, event.msg_args))
        else:
            _log.debug("Unhandled Application Event %s(%s): %s" % (event.dispatcher, msg_id, msg_args))
                

# vim: et ts=4 sts=4
