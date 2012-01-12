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
import math
import collections
import threading
import types
import logging
import time

from gant.ant_api import Future, AntError

_log = logging.getLogger("gant.ant_serial_dialect")

"""
At least this amount of time will we waited
before raising an error stating no reply from
device. Normally the device should reply almost
immediately. But, for Acklowledge (or other
types of data tranfers it may take much longer.
particullary if device is not sync with tx period.
"""
ANT_REPLY_TIMEOUT_MILLIS = 2000

ANT_UNASSIGN_CHANNEL = 0x41
ANT_ASSIGN_CHANNEL = 0x42
ANT_SET_CHANNEL_ID = 0x51
ANT_SET_CHANNEL_PERIOD = 0x43
ANT_SET_CHANNEL_SEARCH_TIMEOUT = 0x44
ANT_SET_CHANNEL_RF_FREQ = 0x45
ANT_SET_NETWORK_KEY = 0x46
ANT_RESET_SYSTEM = 0x4a
ANT_OPEN_CHANNEL = 0x4b
ANT_CLOSE_CHANNEL = 0x4c
ANT_REQUEST_MESSAGE = 0x4d
ANT_BROADCAST_DATA = 0x4e
ANT_ACKNOWLEDGED_DATA = 0x4f
ANT_BURST_TRANSFER_PACKET = 0x50
ANT_STARTUP_MESSAGE = 0x6f
ANT_SERIAL_ERROR_MESSAGE = 0xae
ANT_CHANNEL_RESPONSE_OR_EVENT = 0x40
ANT_CHANNEL_STATUS = 0x52
ANT_VERSION = 0x3e
ANT_CAPABILITIES = 0x54
ANT_SERIAL_NUMBER = 0x61
ANT_OPEN_RX_SCAN_MODE = 0x5b
ANT_SEARCH_WAVEFORM = 0x49

"""
All functions which will be exported by SerialDialect class.
function name, ant msg_id, struct.pack format, method args
"""
ANT_FUNCTIONS = [
    ("unassign_channel", ANT_UNASSIGN_CHANNEL, "B", ["channel_number"]),
    ("assign_channel", ANT_ASSIGN_CHANNEL, "BBB", ["channel_number", "channel_type", "network_number"]),
    ("set_channel_id", ANT_SET_CHANNEL_ID, "BHBB", ["channel_number", "device_number", "device_type_id", "trans_type"]),
    ("set_channel_period", ANT_SET_CHANNEL_PERIOD, "BH", ["channel_number", "message_period"]),
    ("set_channel_search_timeout", ANT_SET_CHANNEL_SEARCH_TIMEOUT, "BB", ["channel_number", "search_timeout"]),
    ("set_channel_rf_freq", ANT_SET_CHANNEL_RF_FREQ, "BB", ["channel_number", "rf_frequency"]),
    ("set_network_key", ANT_SET_NETWORK_KEY, "B8s", ["network_number", "key"]),
    ("reset_system", ANT_RESET_SYSTEM, "x", []),
    ("open_channel", ANT_OPEN_CHANNEL, "B", ["channel_number"]),
    ("close_channel", ANT_CLOSE_CHANNEL, "B", ["channel_number"]),
    ("request_message", ANT_REQUEST_MESSAGE, "BB", ["channel_number", "message_id"]),
    ("send_broadcast_data", ANT_BROADCAST_DATA, "B8s", ["channel_number", "data"]),
    ("send_acknowledged_data", ANT_ACKNOWLEDGED_DATA, "B8s", ["channel_number", "data"]),
    ("send_burst_transfer_packet", ANT_BURST_TRANSFER_PACKET, "B8s", ["channel_number", "data"]),
    ("open_rx_scan_mode", ANT_OPEN_RX_SCAN_MODE, "x", []),
    ("set_search_waveform", ANT_SEARCH_WAVEFORM, "BBx", ["channel_nubmer", "value"]),
]

"""
All supported callbacks which can be unpacked by SerialDialect.unpack.
function_name, ant msg_id, struct.unpack format, namedtuple property names.
"""
ANT_CALLBACKS = [
    ("startup_message", ANT_STARTUP_MESSAGE, "B", ["startup_messsage"]),
    ("serial_error_message", ANT_SERIAL_ERROR_MESSAGE, "B", ["error_number"]),
    ("broadcast_data", ANT_BROADCAST_DATA, "B8s", ["channel_number", "data"]),
    ("acknowledged_data", ANT_ACKNOWLEDGED_DATA, "B8s", ["channel_number", "data"]),
    ("burst_transfer_packet", ANT_BURST_TRANSFER_PACKET, "B8s", ["channel_number", "data"]),
    ("channel_response_or_event", ANT_CHANNEL_RESPONSE_OR_EVENT, "BBB", ["channel_number", "message_id", "message_code"]),
    ("channel_status", ANT_CHANNEL_STATUS, "BB", ["channel_number", "channel_status"]),
    ("channel_id", ANT_SET_CHANNEL_ID, "BHBB", ["channel_number", "device_number", "device_type_id", "man_id"]),
    ("ant_version", ANT_VERSION, "11s", ["version"]),
    ("capabilities", ANT_CAPABILITIES, "BBBBBB", ["max_channels", "max_networks", "standard_options", "advanced_options", "advanced_options2", "reserved"]),
    ("serial_number", ANT_SERIAL_NUMBER, "4s", ["serial_number"]),
]

def millis():
    return int(round(time.time() * 1000))

def generate_checksum(msg):
    """
    Generate a checkum for the provided message.
    xor of all data.
    """
    return reduce(lambda x, y: x ^ y, map(lambda x: ord(x), msg))

def validate_checksum(msg):
    """
    return true if checksum valid.
    """
    return generate_checksum(msg) == 0

def tokenize_message(msg):
    """
    Given a string og ANT messages return an array
    where each elemtn is a string represnting a message.
    """
    result = []
    while msg:
        assert ord(msg[0]) == 0xa4 or ord(msg[0]) == 0xa5
        length = ord(msg[1])
        result.append(msg[:4 + length])
        msg = msg[4 + length:]
    return result


class SerialDialect(object):
    """
    Provides low level access to hardware device.
    """

    def __init__(self, hardware, function_table=ANT_FUNCTIONS, callback_table=ANT_CALLBACKS):
        self._hardware = hardware
        self._dispatcher = Dispatcher(self._hardware)
        self._dispatcher.listener = ListenerGroup()
        self._result_matchers = ListenerGroup()
        self._result_matchers.propagate_none = True
        self._dispatcher.listener.add_listener(self._result_matchers)
        self._enhance(function_table)
        self._callbacks = dict([(c[1], c) for c in callback_table])
        self._dispatcher.start()

    def _enhance(self, function_table):
        """
        Add methods to this instace based on the provided function table.
        """
        for (msg_name, msg_id, msg_format, msg_args) in function_table:
            if not hasattr(self, msg_name):
                def factory(msg_id, msg_name, msg_format, msg_args):
                    def method(self, *args, **kwds):
                        named_args = collections.namedtuple(msg_name, msg_args)(*args, **kwds)
                        return self._exec(msg_id, msg_format, named_args)
                    return method
                setattr(self, msg_name, types.MethodType(factory(msg_id, msg_name, msg_format, msg_args), self, self.__class__))

    def close(self):
        self.__del__()

    def __del__(self):
        _log.debug("Reseting device.")
        self._exec(ANT_RESET_SYSTEM, "x", ()) 
        _log.debug("Stopping dispatcher thread.")
        self._dispatcher.stop()
        _log.debug("Closing hardware.")
        self._hardware.close()

    def reset_system(self):
        self._result_matchers.clear_listeners()
        self._hardware.write("\x00" * 15) # 9.5.2, 15 0's to reset state machine
        result = self._exec(ANT_RESET_SYSTEM, "x", ()) 
        # not all devices sent a reset message, so just sleep
        # incase device needs time to reinitialize
        time.sleep(.25)
        return result

    def get_serial_number(self):
        return self.request_message(0, ANT_SERIAL_NUMBER)

    def get_ant_version(self):
        return self.request_message(0, ANT_VERSION)

    def get_capabilities(self):
        return self.request_message(0, ANT_CAPABILITIES)

    def get_channel_id(self, channel_number):
        return self.request_message(channel_number, ANT_SET_CHANNEL_ID)

    def get_channel_status(self, channel_number):
        return self.request_message(channel_number, ANT_CHANNEL_STATUS)

    def _exec(self, msg_id, msg_format, msg_args):
        """
        Exceute the given commant, returing the async result
        which can be optionally wait()'d on.
        """
        # matcher which select message on input stream as result of this call
        matcher = self._create_matcher(msg_id, msg_args)
        # validator (optional) which checks for an "ok" state from device
        validator = self._create_validator(msg_id, msg_args)
        # create the listener, MUST REGISERED BEFORE WRITE
        listener = Future() if not matcher else MatchingListener(msg_id, self, matcher, validator, millis() + ANT_REPLY_TIMEOUT_MILLIS)
        # build the message
        length = struct.calcsize("<" + msg_format)
        msg = struct.pack("<BBB" + msg_format, 0xA4, length, msg_id, *msg_args)
        msg += chr(generate_checksum(msg))
        # execute the command on hardware
        _log.debug("SEND %s" % msg.encode("hex"))
        if matcher:
            # register a listener to capure input from device and set status
            self._result_matchers.add_listener(listener)
        # the ant protocol specfication allows for two option 0 bytes
        # the windows driver always sends these. I tried leaving them
        # off but this causes timeouts where the the device doesn't reply.
        self._hardware.write(msg + "\x00\x00")
        return listener
    
    def _create_matcher(self, msg_id, msg_args):
        """
        Create a matcher to which is used to match the result
        of the given command when read from device. The matcher
        must be unambious, our the whole pipeline can get messed up.
        """
        expected_msg_id = None
        expected_args = {}
        # older devices don't send a startup message, expect nothing after reset
        if msg_id == ANT_RESET_SYSTEM:
            return None
        # for request_message make sure to set the requested id as expected
        elif msg_id == ANT_REQUEST_MESSAGE:
            if msg_args.message_id in (ANT_CHANNEL_STATUS, ANT_SET_CHANNEL_ID):
                expected_args["channel_number"] = msg_args.channel_number
            expected_msg_id = msg_args.message_id
        # close channel msg_code must be 7
        elif msg_id == ANT_CLOSE_CHANNEL:
            expected_msg_id = ANT_CHANNEL_RESPONSE_OR_EVENT
            expected_args["channel_number"] = msg_args.channel_number
            expected_args["message_id"] = 1 # ??? no citation in ant protocol
            expected_args["message_code"] = 7
        # default, is to look for CHANNEL_RESPONSE_OR_EVENT
        else:
            if hasattr(msg_args, "channel_number"):
                expected_args["channel_number"] = msg_args.channel_number
            expected_msg_id = ANT_CHANNEL_RESPONSE_OR_EVENT
            expected_args["message_id"] = msg_id
        return MessageMatcher(expected_msg_id, **expected_args)

    def _create_validator(self, msg_id, msg_args):
        """
        Optionall create a matcher which returns true
        to inidicate that a 'good' reply was reiceved.
        On false, the async result will throw.
        """
        if msg_id == ANT_REQUEST_MESSAGE or msg_id == ANT_CLOSE_CHANNEL:
            return None
        else:
            return MessageMatcher(ANT_CHANNEL_RESPONSE_OR_EVENT, message_code=0)

    def unpack(self, data):
        """
        Unpack the give by stream to tuple:
        (msg_id, namedtuple(fields))
        """
        try:
            msg_id = ord(data[2])
            msg_length = ord(data[1])
            (msg_name, msg_id, msg_format, msg_args) = self._callbacks[msg_id]
            if msg_id:
                msg_args = collections.namedtuple(msg_name, msg_args)
                real_args = msg_args(*struct.unpack("<" + msg_format, data[3:3 + msg_length]))
                return (msg_id, real_args)
        except (IndexError, KeyError):
            raise AntError("Unsupported message. %s" % data.encode("hex"), AntError.ERR_UNSUPPORTED_MESSAGE)


class MessageMatcher(object):
    """
    Generic implementation of an input message matcher.
    matches against msg_id and a optional list of additional args.
    """
    
    def __init__(self, msg_id, **kwds):
        """
        Create a new matcher which returns true when a message
        with given msg_id is passed to match, and all arguments
        in **kwds match a field of message. e.g. to match 
        ChannelEvent(0x40) replying to message close channel(0x4c):
        MessageMatcher(0x40, message_id=0x4c)
        """
        self.msg_id = msg_id
        self.restrictions = kwds

    def match(self, msg):
        """
        True if the provided message matches criteria
        provided in constructor.
        """
        (msg_id, args) = msg
        if self.msg_id == msg_id:            
            matches = [getattr(args, key) == val for (key, val) in self.restrictions.items()]
            return not matches or reduce(lambda x, y : x and y, matches)
            raise


class MatchingListener(Future):
    """
    A listner which can be restisterd with dispatcher,
    manager an async Future result.
    """
    
    def __init__(self, cmd, dialect, matcher, validator, expiration):
        """
        Manage the give future, updating value or exception
        based on the given matcher and validator.
        """
        self._cmd = cmd
        self._lock = threading.Lock()
        # this lock is made avalible to client via call to 
        # Future.wait(), we hold the lock until this listener
        # decides to remove it self to the listenere queue.
        # at the time we initialize result and execption as
        # appropriate and release lock (allowing any client
        # which was pending complention of this command to continue.
        self._lock.acquire()
        self._dialect = dialect
        self._matcher = matcher
        self._validator = validator
        self._expiration = expiration
        self._result = None
        self._exception = None

    @property
    def result(self):
        self.wait()
        return self._result

    def wait(self):
        with self._lock:
            if self._exception is not None: raise AntError("Command returned error. msg_id=0x%0x" % self._cmd, AntError.ERR_MSG_FAILED)
            elif self._result is None: raise AntError("Command timed out. msg_id=0x%x" % self._cmd, AntError.ERR_TIMEOUT)

    def on_event(self, event, group):
        """
        If matcher matchers, update status of our Future
        and unregister as listener. else continue waiting.
        """
        if millis() > self._expiration:
            group.remove_listener(self)
            self._lock.release()
        elif event is not None:
            parsed_msg = self._dialect.unpack(event)
            if not self._matcher or self._matcher.match(parsed_msg):
                if self._validator and not self._validator.match(parsed_msg):
                    self._exception = True
                else:
                    self._result = parsed_msg[1]
                group.remove_listener(self)
                self._lock.release()
                # don't allow additional matchers to run
                return True


class ListenerGroup(object):
    """
    A listener which delegates to a collection
    of listeners. Each listener in the group
    is recives the even in order, and choose
    if event should continue propgating or stop.
    """
    
    propagate_none = False
    allow_duplicates = False

    def __init__(self):
        self._lock = threading.RLock()
        self._listeners = []

    def add_listener(self, listener):
        with self._lock:
            if not self.allow_duplicates and listener in self._listeners:
                raise AntError("Must wait() before sumbitting same msg_type.", AntError.ERR_API_USAGE)
            else:
                self._listeners.append(listener)

    def remove_listener(self, listener):
        with self._lock: self._listeners.remove(listener)

    def clear_listeners(self):
        with self._lock: self._listeners = []

    def on_event(self, event, group=None):
        if event is not None or self.propagate_none:
            with self._lock:
                # copy the list in case a listener want to modify
                for listener in list(self._listeners):
                    try:
                        if listener.on_event(event, group=self):
                            break
                    except:
                        _log.error("Caught Exception in Listener Group.", exc_info=True)
        

class Dispatcher(threading.Thread):
    """
    Dipatcher thread reads from low level
    hardware byte stream a delegates all
    messages to the configured listener.
    """

    daemon = True
    listener = None

    def __init__(self, hardware):
        super(Dispatcher, self).__init__()
        self._hardware = hardware
        self._stopped = False
    
    def run(self):
        while not self._stopped:
            try:
                raw_string = self._hardware.read(timeout=1000);
                for msg in tokenize_message(raw_string) or (None,):
                    # None is published to listners even if no message.
                    # Command matchers need to be notified of None to
                    # be able to timepout when nothing is recieved.
                    if msg is not None: _log.debug("RECV %s" % msg.encode("hex"))
                    self.listener.on_event(event=msg)
            except:
                _log.error("Caught Exception in Dispatcher Thread.", exc_info=True)
            
    def stop(self):
        self._stopped = True
        self.join(1)


# vim: et ts=4 sts=4
