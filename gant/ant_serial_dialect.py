import struct
import math
import collections
import threading
import types
import logging

_log = logging.getLogger("gant.ant_serial_dialect")

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
ANT_ANT_VERSION = 0x3e
ANT_CAPABILITIES = 0x54
ANT_SERIAL_NUMBER = 0x61

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
    ("broadcast_data", ANT_BROADCAST_DATA, "B8s", ["channel_number", "data"]),
    ("acknowledged_data", ANT_ACKNOWLEDGED_DATA, "B8s", ["channel_number", "data"]),
    ("burst_transfer_packet", ANT_BURST_TRANSFER_PACKET, "B8s", ["channel_number", "data"]),
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
    ("ant_version", ANT_ANT_VERSION, "11s", ["version"]),
    ("capabilities", ANT_CAPABILITIES, "BBBBBB", ["max_channels", "max_networks", "standard_options", "advanced_options", "advanced_options2", "reserved"]),
    ("serial_number", ANT_SERIAL_NUMBER, "4s", ["serial_number"]),
]

"""
Map ANT message sent to device with response which should be expected
from device. Messages should be list here iff the can be coorelated with
a unqiue expected response, and they will never be sent in an async fashion.
Mixing usage of sync and async calling for same message id can not be supported
since coorelation of replies is ambigous. So, config messages can be lised here,
but probably not much else. For message ids that are included, there injected
methods on SerialDialect will behave synchronously (blocking until config operation
is complete) msg_id -> MessageMatcher
"""
ANT_SYNC_MATCHERS = {
    ANT_UNASSIGN_CHANNEL: (ANT_CHANNEL_RESPONSE_OR_EVENT, {"message_id": ANT_UNASSIGN_CHANNEL}),
}
"""
Device a matcher which returns true to inicate teh synchronis reply is valid.
"""
ANT_VALID_MATCHERS = {
    ANT_UNASSIGN_CHANNEL: (ANT_CHANNEL_RESPONSE_OR_EVENT, {"message_code": 0}),
}

class SerialDialect(object):

    def __init__(self, hardware, dispatcher, function_table=ANT_FUNCTIONS, callback_table=ANT_CALLBACKS):
        self._hardware = hardware
        self._dispatcher = dispatcher
        self._enhance(function_table)
        self._callbacks = dict([(c[1], c) for c in callback_table])

    def _enhance(self, function_table):
        for (msg_name, msg_id, msg_format, msg_args) in function_table:
            if not hasattr(self, msg_name):
                def factory(msg_id, msg_name, msg_format, msg_args):
                    def method(self, *args, **kwds):
                        sync_matcher = MessageMatcher.from_rules_tuple(self, ANT_SYNC_MATCHERS[msg_id]) if ANT_SYNC_MATCHERS.has_key(msg_id) else None
                        valid_matcher = MessageMatcher.from_rules_tuple(self, ANT_VALID_MATCHERS[msg_id]) if ANT_VALID_MATCHERS.has_key(msg_id) else None
                        self._exec(msg_id, msg_format, collections.namedtuple(msg_name, msg_args), sync_matcher, valid_matcher, args, kwds)
                    return method
                setattr(self, msg_name, types.MethodType(factory(msg_id, msg_name, msg_format, msg_args), self, self.__class__))

    def _exec(self, msg_id, msg_format, msg_args, sync_matcher, validation_matcher, args, kwds):
        listener = None
        event = None
        real_args = msg_args(*args, **kwds)
        length = struct.calcsize(msg_format)
        msg = struct.pack("<BBB" + msg_format, 0xA4, length, msg_id, *real_args)
        msg += chr(self.generate_checksum(msg))
        _log.debug("SEND %s" % msg.encode("hex"))
        if sync_matcher:
            # this method's configured for synchronis call
            # register an event lister we can wait on
            listener = MatchingListener(sync_matcher)
            event = listener.is_matched_event
            self._dispatcher.add_listener(listener)
        self._hardware.write(msg)
        if event:
            event.wait(1)
            assert event.is_set()
            assert not validation_matcher or validation_matcher.match(listener.msg)
            return self.unpack(listener.msg)

    def unpack(self, data):
        msg_id = ord(data[2])
        msg_length = ord(data[1])
        (msg_name, msg_id, msg_format, msg_args) = self._callbacks[msg_id]
        msg_args = collections.namedtuple(msg_name, msg_args)
        real_args = msg_args(*struct.unpack(msg_format, data[3:3 + msg_length]))
        return (msg_id, real_args)

    def generate_checksum(self, msg):
        return reduce(lambda x, y: x ^ y, map(lambda x: ord(x), msg))

    def validate_checksum(self, msg):
        return self.generate_checksum(msg) == 0


class MessageMatcher(object):
    
    @classmethod
    def from_rules_tuple(cls, dialect, rules):
        (msg_id, kwds) = rules
        return MessageMatcher(dialect, msg_id, **kwds)

    def __init__(self, dialect, msg_id, **kwds):
        self._dialect = dialect
        self._restrictions = kwds
        self._msg_id = msg_id

    def match(self, msg):
        msg_id = None
        args = ()
        try:
            (msg_id, args) = self._dialect.unpack(msg)
        except IndexError:
            _log.debug("%s not implemented" % msg.encode("hex"))
        if self._msg_id == msg_id:            
            try:
                matches = [getattr(args, key) == val for (key, val) in self._restrictions.items()]
                return not matches or reduce(lambda x, y : x and y, matches)
            except AttributeError:
                _log.error("Failed to evaluation matcher restrictions", exc_info=True)
                raise


class MatchingListener(object):
    
    is_matched_event = threading.Event()

    def __init__(self, matcher):
        self.matcher = matcher

    def on_message(self, dispatcher, msg):
        if self.matcher.match(msg):
            self.msg = msg
            dispatcher.remove_listener(self)
            self.is_matched_event.set()


class Dispatcher(threading.Thread):

    _lock = threading.Lock()
    _listeners = set() 
    _stopped = False

    def __init__(self, hardware):
        super(Dispatcher, self).__init__()
        self.daemon = True
        self._hardware = hardware
    
    def add_listener(self, listener):
        with self._lock:
            self._listeners.add(listener)

    def remove_listener(self, listener):
        with self._lock:
            self._listeners.remove(listener)

    def run(self):
        while not self._stopped:
            msg = self._hardware.read(timeout=1000);
            if msg:
                _log.debug("RECV %s" % msg.encode("hex"))
                listeners = None
                with self._lock:
                    listeners = list(self._listeners)
                for listener in listeners:
                    try:
                        listener.on_message(self, msg)
                    except:
                        _log.error("Caught Exception from listener %s." % listener, exc_info=True)
        
    def stop(self):
        self._stopped = True
        return self


# vim: et ts=4 sts=4
