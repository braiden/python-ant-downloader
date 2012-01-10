import struct
import math
import collections
import threading
import types
import logging
import time

from gant.ant_api import Future

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
ANT_VERSION = 0x3e
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
    ("ant_version", ANT_VERSION, "11s", ["version"]),
    ("capabilities", ANT_CAPABILITIES, "BBBBBB", ["max_channels", "max_networks", "standard_options", "advanced_options", "advanced_options2", "reserved"]),
    ("serial_number", ANT_SERIAL_NUMBER, "4s", ["serial_number"]),
]

class SerialDialect(object):
    """
    Provides low level access to hardware device.
    """

    def __init__(self, hardware, dispatcher, function_table=ANT_FUNCTIONS, callback_table=ANT_CALLBACKS):
        self._hardware = hardware
        self._dispatcher = dispatcher
        self._enhance(function_table)
        self._callbacks = dict([(c[1], c) for c in callback_table])

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
        self._dispatcher.stop().join()
        self._hardware.close()

    def reset_system(self):
        self._dispatcher.clear_listeners()
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
        # create a future to represent the result of this call
        result = Future()
        # assign a function which will cause this operation to be retried
        def retry(): return self._exec(msg_id, msg_format, msg_args)
        result.retry = retry
        # matcher which select message on input stream as result of this call
        matcher = self._create_matcher(msg_id, msg_args)
        # validator (optional) which checks for an "ok" state from device
        validator = self._create_validator(msg_id, msg_args)
        # create the listener, MUST REGISERED BEFORE WRITE
        listener = None if not matcher else MatchingListener(self, result, matcher, validator)
        # build the message
        length = struct.calcsize("<" + msg_format)
        msg = struct.pack("<BBB" + msg_format, 0xA4, length, msg_id, *msg_args)
        msg += chr(self.generate_checksum(msg))
        # execute the command on hardware
        _log.debug("SEND %s" % msg.encode("hex"))
        if listener:
            # register a listener to capure input from device and set status
            self._dispatcher.add_listener(listener)
        else:
            # no listener flag as immediate success
            result.result = None
        self._hardware.write(msg + "\x00\x00")
        return result
    
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
        msg_id = ord(data[2])
        msg_length = ord(data[1])
        (msg_name, msg_id, msg_format, msg_args) = self._callbacks[msg_id]
        msg_args = collections.namedtuple(msg_name, msg_args)
        real_args = msg_args(*struct.unpack("<" + msg_format, data[3:3 + msg_length]))
        return (msg_id, real_args)

    def generate_checksum(self, msg):
        """
        Generate a checkum for the provided message.
        xor of all data.
        """
        return reduce(lambda x, y: x ^ y, map(lambda x: ord(x), msg))

    def validate_checksum(self, msg):
        """
        return true if checksum valid.
        """
        return self.generate_checksum(msg) == 0


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
        self._msg_id = msg_id
        self._restrictions = kwds

    def match(self, msg):
        """
        True if the provided message matches criteria
        provided in constructor.
        """
        (msg_id, args) = msg
        if self._msg_id == msg_id:            
            try:
                matches = [getattr(args, key) == val for (key, val) in self._restrictions.items()]
                return not matches or reduce(lambda x, y : x and y, matches)
            except AttributeError:
                _log.error("Failed to evaluation matcher restrictions", exc_info=True)
                raise

    def __str__(self):
        return "<MessageMatcher(0x%0x)%s>" % (self._msg_id, self._restrictions)


class MatchingListener(object):
    """
    A listner which can be restisterd with dispatcher,
    manager an async Future result.
    """

    def __init__(self, dialect, future, matcher, validator):
        """
        Manage the give future, updating value or exception
        based on the given matcher and validator.
        """
        self._dialect = dialect
        self._matcher = matcher
        self._future = future
        self._validator = validator

    def on_message(self, dispatcher, msg):
        """
        If matcher matchers, update status of our Future
        and unregister as listener. else continue waiting.
        """
        try:
            parsed_msg = self._dialect.unpack(msg)
            if not self._matcher or self._matcher.match(parsed_msg):
                if self._validator and not self._validator.match(parsed_msg):
                    self._future.set_exception(AssertionError("Matcher %s reject reply." % self._validator))
                else:
                    self._future.result = parsed_msg[1]
                dispatcher.remove_listener(self)
                # don't allow additional matchers to run
                return True
        except IndexError:
            _log.debug("Unimplemented messsage %s", msg.encode("hex"))


class Dispatcher(threading.Thread):
    """
    Dipatchers low level (raw) byte streams read from
    hardware to any registered liseners.
    """

    daemon = True

    def __init__(self, hardware):
        super(Dispatcher, self).__init__()
        self._lock = threading.Lock()
        self._listeners = []
        self._hardware = hardware
        self._stopped = False
    
    def add_listener(self, listener):
        """
        Add a new listners, listners are notified
        in oreder of earliest registration first.
        """
        with self._lock:
            self._listeners.append(listener)

    def remove_listener(self, listener):
        """
        Remove a listener. Returing from this method
        doesn't quite guarentee that listnere will never
        be called again.
        """
        with self._lock:
            self._listeners.remove(listener)
    
    def clear_listeners(self):
        """
        Remove all listners currently associated.
        """
        with self._lock:
            self._listeners = []
    
    def run(self):
        """
        Thread loop.
        """
        while not self._stopped:
            msg = self._hardware.read(timeout=100);
            if msg:
                _log.debug("RECV %s" % msg.encode("hex"))
                listeners = None
                with self._lock:
                    listeners = list(self._listeners)
                for listener in listeners:
                    try:
                        # listener can return true to indicate no future 
                        # instances shoudl be notified
                        if listener.on_message(self, msg):
                            break
                    except:
                        _log.error("Caught Exception from listener %s." % listener, exc_info=True)
        
    def stop(self):
        """
        Stop the thread.
        """
        self._stopped = True
        return self


# vim: et ts=4 sts=4
