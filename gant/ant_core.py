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

import struct
import collections
import types
import logging
import array


_log = logging.getLogger("gant.ant_core")
_open_resources = set()

ANT_SYNC = 0xa4

class MessageType(object):
    UNASSIGN_CHANNEL = 0x41
    ASSIGN_CHANNEL = 0x42
    CHANNEL_ID = 0x51
    CHANNEL_PERIOD = 0x43
    CHANNEL_SEARCH_TIMEOUT = 0x44
    CHANNEL_RF_FREQ = 0x45
    NETWORK_KEY = 0x46
    RESET_SYSTEM = 0x4a
    OPEN_CHANNEL = 0x4b
    CLOSE_CHANNEL = 0x4c
    REQUEST_MESSAGE = 0x4d
    BROADCAST_DATA = 0x4e
    ACKNOWLEDGED_DATA = 0x4f
    BURST_TRANSFER_PACKET = 0x50
    OPEN_RX_SCAN_MODE = 0x5b
    SEARCH_WAVEFORM = 0x49
    STARTUP_MESSAGE = 0x6f
    SERIAL_ERROR_MESSAGE = 0xae
    CHANNEL_RESPONSE_OR_EVENT = 0x40
    CHANNEL_STATUS = 0x52
    VERSION = 0x3e
    CAPABILITIES = 0x54
    SERIAL_NUMBER = 0x61

class RfEventType(object):
    RX_SEARCH_TIMEOUT = 1
    RX_FAIL = 2
    TX =3
    TRANSFER_RX_FAILED = 4
    TRANSFER_TX_COMPLETED = 5
    TRANSFER_TX_FAILED = 6
    CHANNEL_CLOSED = 7
    RX_FAIL_TO_TO_SEARCH = 8
    CHANNEL_COLLISION = 9
    TRANSFER_TX_START = 10
    SERIAL_QUEUE_OVERFLOW = 52
    QUEUE_OVERFLOW = 53

class ChannelEventType(object):
    NO_ERROR = 0
    CHANNEL_IN_WRONG_STATE = 21
    CHANNEL_NOT_OPENED = 22
    CHANNEL_ID_NOT_SET = 24
    CLOSE_ALL_CHANNELS = 25
    TRANSFER_IN_PROGRESS = 31
    TRANSFER_SEQUENCE_NUMBER_ERROR = 32
    TANNSFER_IN_ERROR = 33
    MESSAGE_SIZE_EXCEEDS_LIMIT = 39
    INVALID_MESSAGE = 40
    INVALID_NETWORK_NUMBER = 41
    INVALID_LIST_ID = 48
    INVALID_SCAN_TX_CHANNEL = 49
    INVALID_PARAMETER_PROVIDED = 51
    NVM_FULL_ERROR = 64
    NVM_WRITE_ERROR = 65
    USB_STRING_WRITE_FAIL = 112
    MESG_SERIAL_ERROR_ID = 174

"""
Map of ANT msg_id -> struct.pack format.
Used when sending a message to ANT device.
"""
ANT_PACK_FORMATS = {
    MessageType.UNASSIGN_CHANNEL: "B",
    MessageType.ASSIGN_CHANNEL: "BBB",
    MessageType.CHANNEL_ID: "BHBB",
    MessageType.CHANNEL_PERIOD: "BH",
    MessageType.CHANNEL_SEARCH_TIMEOUT: "BB",
    MessageType.CHANNEL_RF_FREQ: "BB",
    MessageType.NETWORK_KEY: "B8s",
    MessageType.RESET_SYSTEM: "x",
    MessageType.OPEN_CHANNEL: "B",
    MessageType.CLOSE_CHANNEL: "B",
    MessageType.REQUEST_MESSAGE: "BB",
    MessageType.BROADCAST_DATA: "B8s",
    MessageType.ACKNOWLEDGED_DATA: "B8s",
    MessageType.BURST_TRANSFER_PACKET: "B8s",
    MessageType.OPEN_RX_SCAN_MODE: "x",
    MessageType.SEARCH_WAVEFORM: "BBx",
}

"""
Map of ANT msg_id -> struct.unpack format.
Used when received a message from ANT device.
"""
ANT_UNPACK_FORMATS = {
    MessageType.STARTUP_MESSAGE: "B",
    MessageType.BROADCAST_DATA: "B8s",
    MessageType.ACKNOWLEDGED_DATA: "B8s",
    MessageType.BURST_TRANSFER_PACKET: "B8s",
    MessageType.CHANNEL_RESPONSE_OR_EVENT: "BBB",
    MessageType.CHANNEL_STATUS: "BB",
    MessageType.CHANNEL_ID: "BHBB",
    MessageType.VERSION: "11s",
    MessageType.CAPABILITIES: "BBBBBB",
    MessageType.SERIAL_NUMBER: "4s",
}

def generate_checksum(msg):
    """
    Given string, msg, representing a packed
    ANT message calculate the checksum.
    """
    return reduce(lambda x, y: x ^ y, array.array("B", msg))

def validate_checksum(msg):
    """
    Given string, msg, representing a packed
    ANT message return true if checksum valid.
    """
    return generate_checksum(msg) == 0

def tokenize_message(msg):
    """
    Given a string, msg, which could contain
    one or more contatndated ANT messages,
    return an array of messages contained in string.
    """
    result = []
    while msg:
        assert ord(msg[0]) & 0xFE == ANT_SYNC
        length = ord(msg[1])
        result.append(msg[:4 + length])
        msg = msg[4 + length:]
    return result

def value_of(enum, const):
    """
    Return name of property in class enum
    have the constance value const.
    """
    for (k, v) in enum.__dict__.items():
        if v == const: return k


class Marshaller(object):
    """
    Impelemnted basic functionality
    for coverting positional args to ANT
    message byte streams.
    """
    
    def __init__(self, pack_formats=ANT_PACK_FORMATS, unpack_formats=ANT_UNPACK_FORMATS):
        self.pack_formats = pack_formats
        self.unpack_formats = unpack_formats
        
    def pack(self, msg_id, msg_args):
        """
        Create message fro givem message id,
        raises IndexError/struct.error on invalid input.
        """
        msg_format = self.pack_formats[msg_id]
        length = struct.calcsize("<" + msg_format)
        msg = struct.pack("<BBB" + msg_format, ANT_SYNC, length, msg_id, *msg_args)
        return msg + chr(generate_checksum(msg))
        
    def unpack(self, msg):
        """
        Create tuple of args representing ANT message.
        raises AssertionError, IndexError, struct.error
        on un parsable messages.
        """
        assert validate_checksum(msg)
        msg_id = ord(msg[2])
        msg_format = self.unpack_formats[msg_id]
        msg_length = ord(msg[1])
        msg_args = struct.unpack("<" + msg_format, msg[3:3 + msg_length])
        return (msg_id, msg_args)
        

class Dispatcher(object):
    """
    Provides read / write access to hardware
    as well as loop() method for running async
    state machine to send/receive ant messages.
    """

    """
    How long read blocks on usb hardware
    when no message is avaible.
    """
    timeout = 1000

    def __init__(self, hardware, marshaller):
        self.hardware = hardware
        self.marshaller = marshaller

    def send(self, msg_id, *msg_args):
        """
        Write given message to ant device,
        returning after write complete.
        No status is reported, expecpt that
        message was commited to usb on non-exception.
        """
        msg = self.marshaller.pack(msg_id, args)
        _log.debug("SEND %s" % msg.encode("hex"))
        self.hardware.write(msg + "\x00\x00")

    def recv(self):
        """
        Return an array of ANT messages which
        were currently waiting to be read from
        input stream.
        """
        msgs = self.hardware.read(timout=self.timeout)
        return None if msgs is None else [self.marshaller.unpack(msg) for msg in tokenize_message(msgs)]

    def loop(self, listener):
        """
        Execute the current listener in current
        thread. Method returns once listener
        has no return values.
        """
        msgs = []
        while True:
            try:
                if not msgs:
                    msgs = self.recv()
                msg = msgs[0]
                del msgs[0]
                _log.debug("RECV %s" % msg.encode("hex"))
                if listener.on_message(msg) is None:
                    return listener
            except Exception as e:
                _log.debug("Dispatcher caught exception in listener.", exc_info=True)
            

class Listener(object):
    """
    Interface for classes wanting to recive
    low level parsed any messages from Dispatcher.
    Create listener, and pass in to loop.
    """

    def on_message(self, msg):
        """
        Accept a single parsed ANT message from input.
        If method returns no value Dispatcher.loop will terminate.
        """
        pass


class AsyncCommandExecutionListener(Listener):
    """
    A Dispatcher Listener which delegates messages
    as a higher level "Event" object to "AsynCommand"s.
    AsyncCommands can be built in a hierachial fashion
    with the root command build on top of other command
    which provide a translation. e.g. an AsyncDeviceSetupCommand
    can invoke AsyncAssignChannelId command. AntFsCommand
    can invoke AntFsFindBeaconCommand... see ant_commands
    """

    result = None

    def __init__(self, async_command, dispatcher, parent=None):
        self.async_command = async_command
        self.children = []
        self.parent = parent
        self.dispatcher = dispatcher

    def on_message(self, msg):
        """
        Dispatcher the given event to any children of async
        command managed by this instance. The distinct results
        from the children are all passed into the async manged
        by this instance.
        """
        # the resulted results must be unique'd
        results = set()
        # need to keep track of if the command is invoked with output of any children
        command_called = False
        # keep track of is the command managed by this instance flagged itself as done
        command_done = True
        for child in list(self.children):
            # invoke the child command (possibly recursively)
            events = child.on_message(msg)
            for event in events: 
                command_called = True
                # invoke this command with each of the child results
                ctx = AsyncCommandExecutionContext(self.dispatcher, self)
                result = self.async_command.on_event(ctx, event)
                if result: results.add(result)
                # if the command says its done, we dont' send it anymore events
                if ctx.done: 
                    self.result = result
                    break
            else:
                continue
            break
        else:
            if not command_called:
                # if this command has no children, or chilren returned nothing, pass-thru event
                ctx = AsyncCommandExecutionContext(self.dispatcher, self)
                result = self.async_command.on_event(ctx, msg)
                if result: results.add(result)
                if ctx.done:
                    self.result = result
                else:
                    command_done = False
        # remove this command from parent if requested
        if command_done and self.parent:
            self.parent.remove_command(self.async_command)
        # the Root node returns None if its empty and result-less (to terminate dispatcher loop)
        return None if not self.parent and not self.children and not results else results
            
    def add_command(self, async_command):
        """
        Add A command to execute before the one currently being managed.
        The command can dispatch its own event types to the parent, or filter
        and messages.
        """
        listener = AsyncCommandExecutionListener(async_command, self.dispatcher, self)
        self.children.append(listener)
        ctx = AsyncCommandExecutionContext(self.dispatcher, listener)
        async_command.on_event(ctx, AsyncCommandEvent(AsyncCommandEvent.COMMAND_ADDED))

    def remove_command(self, async_command):
        """
        Remove the given command from this parent.
        """
        self.children = [c for c in self.children if c.async_command != async_command]


class AsyncCommandExecutionContext(object):
    """
    The AsyncCommandExecutionConetxt is passed into commands.
    It provides access to send data over ant as well as manages
    it's child commands.
    """

    """
    Commands should update this flag to true to indicate
    they are done. No further events would be dispatched.
    """
    done = False

    def __init__(self, dispatcher, listener):
        self.dispatcher = dispatcher
        self.listener = listener

    def send(self, msg_id, *msg_args):
        """
        Delegate to Dispatcher.send
        """
        self.dispatcher.send(msg_id, *msg_args)

    def add_command(self, async_command):
        """
        Delegate to AsyncCommandExecutionListener.add_command
        """
        self.listener.add_command(async_command)

    def remove_command(self, async_command):
        """
        Delegate to AsyncCommandExecutionListener.remove_command
        """
        self.listener.remove_command(async_command)
        

class AsyncCommandEvent(object):
    
    """
    Event sent to newly created Commands as soon as they
    are registered with parent.
    """
    COMMAND_ADDED = 0

    source = AsyncCommandExecutionListener
    msg_id = None

    def __init__(self, msg_id):
        self.msg_id = msg_id


class DispatcherEvent(object):
    """
    Lowest level event, containing the ANT
    msg_id an any arguments as unpacked by marshaller.
    """
   
    source = Dispatcher
    msg_id = None
    msg_args = None

    def __init__(self, msg_id, msg_args):
        self.msg_id = msg_id
        self.msg_args = msg_args


class AsyncCommand(object):
    """
    State maching which will receive callbacks
    for each ant message. Context provides means
    of sending message, or building more advanced
    commands by filtering through other AsyncCommand
    """
    
    def on_event(self, context, event):
        pass


class LoggingAsyncCommand(AsyncCommand):
    """
    Default implemenation for a Root AsyncCommand.
    Any Messages which are not filtered (processed)
    by a child AsyncCommand are logged to debug.
    """

    def on_event(self, context, event):
        if event.source == Dispatcher:
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
