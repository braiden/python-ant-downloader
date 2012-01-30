# Copyright (c) 2012, Braiden Kindt.
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
# 
#   1. Redistributions of source code must retain the above copyright
#      notice, this list of conditions and the following disclaimer.
# 
#   2. Redistributions in binary form must reproduce the above
#      copyright notice, this list of conditions and the following
#      disclaimer in the documentation and/or other materials
#      provided with the distribution.
# 
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDER AND CONTRIBUTORS
# ''AS IS'' AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
# LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS
# FOR A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE
# COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT,
# INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
# LIABILITY, OR TORT(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY
# WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.


import threading
import logging
import array
import errno
import time
import struct
import collections

_LOG = logging.getLogger("antagent.ant")

# first byte of an packet
SYNC = 0xA4
# direction of command
DIR_IN = "IN"
DIR_OUT = "OUT"
# channel response codes
RESPONSE_NO_ERROR = 0
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
# rf event codes
EVENT_RX_SEARCH_TIMEOUT = 1
EVENT_RX_FAIL = 2
EVENT_TX = 3
EVENT_TRANSFER_RX_FAILED = 4
EVENT_TRANSFER_TX_COMPLETED = 5
EVENT_TRANSFER_TX_FAILED = 6
EVENT_CHANNEL_CLOSED = 7
EVENT_RX_FAIL_TO_SEARCH = 8
EVENT_CHANNEL_COLLISION = 9
EVENT_TRANSFER_TX_START = 10
EVENT_SERIAL_QUEUE_OVERFLOW = 52
EVENT_QUEUE_OVERFLOW = 53

def msg_to_string(msg):
    """
    Retruns a string representation of
    the provided array (for debug output)
    """
    return array.array("B", msg).tostring().encode("hex")

def generate_checksum(msg):
    """
    Generate a checksum of the given msg.
    xor of all bytes.
    """
    return reduce(lambda x, y: x ^ y, msg)

def validate_checksum(msg):
    """
    Retrun true if message has valid checksum
    """
    return generate_checksum(msg) == 0

def tokenize_message(msg):
    """
    A generator returning on ant messages
    from the provided string of one or more
    conacatinated messages.
    """
    while msg:
        assert msg[0] & 0xFE == SYNC
        length = msg[1]
        yield msg[:4 + length]
        msg = msg[4 + length:]

def data_tostring(data):
    """
    Return a string repenting bytes of given
    data. used by send() methods to convert
    arugment to required string.
    """
    if isinstance(data, list):
        return array.array("B", data).tostring()
    elif isinstance(data, array.array):
        return data.tostring()
    else:
        return data

# retry policies define the strategy used to
# determin if a command should be retried based
# on provided error. They can be configured
# for each ANT message defined below. Retry
# on timeout should be considered dangerous.
# e.g. retrying a timedout acknowledged message
# will certainly fail.

def timeout_retry_policy(error):
    return isinstance(error, IOError) and error[0] in (errno.EAGAIN or errno.ETIMEDOUT)

def default_retry_policy(error):
    return isinstance(error, IOError) and error[0] == errno.EAGAIN

def always_retry_policy(error):
    return True

def never_retry_policy(error):
    return False

# matcher define the strategry to determine
# if an incoming message from ANT device sould
# udpate the status of a running command.

def same_channel_or_network_matcher(request, reply):
    return (
            (not hasattr(reply, "channel_number")
             or (hasattr(request, "channel_number") and request.channel_number == reply.channel_number))
        or 
            (not hasattr(reply, "network_number")
             or (hasattr(request, "network_number") and request.network_number == reply.network_number)))

def default_matcher(request, reply):
    return (same_channel_or_network_matcher(request, reply) 
            and isinstance(reply, ChannelEvent)
            and reply.msg_id == request.ID)

def reset_matcher(request, reply):
    return isinstance(reply, StartupMessage)

def close_channel_matcher(request, reply):
    return same_channel_or_network_matcher(request, reply) and (
            (isinstance(reply, ChannelEvent)
             and reply.msg_id == request.ID
             and reply.msg_code != 0)
        or (isinstance(reply, ChannelEvent)
             and reply.msg_id == 1
             and reply.msg_code == EVENT_CHANNEL_CLOSED))

def request_message_matcher(request, reply):
    return default_matcher(request, reply) or reply.ID == request.msg_id

def recv_broadcast_matcher(request, reply):
    return (close_channel_matcher(request, reply)
        or isinstance(reply, RecvBroadcastData))

def send_data_matcher(request, reply):
    return (close_channel_matcher(request, reply)
        or (isinstance(reply, ChannelEvent)
            and reply.msg_id == 1
            and reply.msg_code in (EVENT_TX, EVENT_TRANSFER_TX_COMPLETED, EVENT_TRANSFER_TX_FAILED)))

# validators define stragegy for determining
# if a give reply from ANT should raise an
# error. 

def default_validator(request, reply):
    if isinstance(reply, ChannelEvent) and reply.msg_code in (EVENT_CHANNEL_CLOSED, CHANNEL_NOT_OPENED):
        return IOError(errno.EBADF, "Channel closed. %s" % reply)
    elif isinstance(reply, ChannelEvent) and reply.msg_code != RESPONSE_NO_ERROR:
        return IOError(errno.EINVAL, "Failed to execute command message_code=%d. %s" % (reply.msg_code, reply))

def close_channel_validator(request, reply):
    if not (isinstance(reply, ChannelEvent) and reply.msg_id == 1 and reply.msg_code == EVENT_CHANNEL_CLOSED):
        return default_validator(request, reply)

def send_data_validator(request, reply):
    if isinstance(reply, ChannelEvent) and reply.msg_id == 1 and reply.msg_code == EVENT_TRANSFER_TX_FAILED:
        return IOError(errno.EAGAIN, "Send message was not acknowledged by peer. %s" % reply)
    elif not (isinstance(reply, ChannelEvent) and reply.msg_id == 1 and reply.msg_code in (EVENT_TX, EVENT_TRANSFER_TX_COMPLETED)):
        return default_validator(request, reply)

def send_burst_validator(request, reply):
    # TRANSFER_IN_PROGRESS is sent from device during a burst when queuing
    # additional packets. WHY?? the burst is transmitted successfully, not
    # sure if i'm using some part of API wrong?? For now, we ignore the event
    # after TX_START has been seen.
    if not hasattr(request, "first_packet_seen"):
        if not (isinstance(reply, ChannelEvent) and reply.msg_id == request.ID and reply.msg_code == TRANSFER_IN_PROGRESS):
            return send_data_validator(request, reply)
    else:
        request.first_packet_seen = True
        return send_data_validator(request, reply)

def message(direction, name, id, pack_format, arg_names, retry_policy=default_retry_policy, matcher=default_matcher, validator=default_validator):
    """
    Return a class supporting basic packing
    operations with the give metadata.
    """
    # pre-create the struct used to pack/unpack this message format
    if pack_format:
        byte_order_and_size = ""
        if pack_format[0] not in ("@", "=", "<", ">", "!"):
            # apply default by order and size
            byte_order_and_size = "<"
            msg_struct = struct.Struct(byte_order_and_size + pack_format)
    else:
        msg_struct = None

    # create named-tuple used to converting *arg, **kwds to this messages args
    msg_arg_tuple = collections.namedtuple(name, arg_names)

    # class representing the message definition pased to this method
    class Message(object):

        DIRECTION = direction
        NAME = name
        ID = id

        def __init__(self, *args, **kwds):
            tuple = msg_arg_tuple(*args, **kwds)
            self.__dict__.update(tuple._asdict())

        @property
        def args(self):
            return msg_arg_tuple(**dict((k, v) for k, v in self.__dict__.items() if k in arg_names))

        @classmethod
        def unpack_args(cls, packed_args):
            try: return Message(*msg_struct.unpack(packed_args))
            except AttributeError: return Message(*([None] * len(arg_names)))

        def pack_args(self):
            try: return msg_struct.pack(*self.args)
            except AttributeError: pass
        
        def pack_size(self):
            try: return msg_struct.size
            except AttributeError: return 0

        def is_retryable(self, err):
            return retry_policy(err)

        def is_reply(self, cmd):
            return matcher(self, cmd)

        def validate_reply(self, cmd):
            return validator(self, cmd)

        def __str__(self):
            return str(self.args)

    return Message

# ANT Message Protocol Definitions
UnassignChannel = message(DIR_OUT, "UNASSIGN_CHANNEL", 0x41, "B", ["channel_number"], retry_policy=timeout_retry_policy)
AssignChannel = message(DIR_OUT, "ASSIGN_CHANNEL", 0x42, "BBB", ["channel_number", "channel_type", "network_number"], retry_policy=timeout_retry_policy)
SetChannelId = message(DIR_OUT, "SET_CHANNEL_ID", 0x51, "BHBB", ["channel_number", "device_number", "device_type_id", "trans_type"], retry_policy=timeout_retry_policy)
SetChannelPeriod = message(DIR_OUT, "SET_CHANNEL_PERIOD", 0x43, "BH", ["channel_number", "messaging_period"], retry_policy=timeout_retry_policy) 
SetChannelSearchTimeout = message(DIR_OUT, "SET_CHANNEL_SEARCH_TIMEOUT", 0x44, "BB", ["channel_number", "search_timeout"], retry_policy=timeout_retry_policy)
SetChannelRfFreq = message(DIR_OUT, "SET_CHANNEL_RF_FREQ", 0x45, "BB", ["channel_number", "rf_freq"], retry_policy=timeout_retry_policy)
SetNetworkKey = message(DIR_OUT, "SET_NETWORK_KEY", 0x46, "B8s", ["network_number", "network_key"], retry_policy=timeout_retry_policy)
ResetSystem = message(DIR_OUT, "RESET_SYSTEM", 0x4a, "x", [], retry_policy=always_retry_policy, matcher=reset_matcher)
OpenChannel = message(DIR_OUT, "OPEN_CHANNEL", 0x4b, "B", ["channel_number"], retry_policy=timeout_retry_policy)
CloseChannel = message(DIR_OUT, "CLOSE_CHANNEL", 0x4c, "B", ["channel_number"], retry_policy=timeout_retry_policy, matcher=close_channel_matcher, validator=close_channel_validator)
RequestMessage = message(DIR_OUT, "REQUEST_MESSAGE", 0x4d, "BB", ["channel_number", "msg_id"], retry_policy=timeout_retry_policy, matcher=request_message_matcher)
SetSearchWaveform = message(DIR_OUT, "SET_SEARCH_WAVEFORM", 0x49, "BH", ["channel_number", "waveform"], retry_policy=timeout_retry_policy)
SendBroadcastData = message(DIR_OUT, "SEND_BROADCAST_DATA", 0x4e, "B8s", ["channel_number", "data"], matcher=send_data_matcher, validator=send_data_validator)
SendAcknowledgedData = message(DIR_OUT, "SEND_ACKNOWLEDGED_DATA", 0x4f, "B8s", ["channel_number", "data"], matcher=send_data_matcher, validator=send_data_validator)
SendBurstTransferPacket = message(DIR_OUT, "SEND_BURST_TRANSFER_PACKET", 0x50, "B8s", ["channel_number", "data"], matcher=send_data_matcher, validator=send_burst_validator)
StartupMessage = message(DIR_IN, "STARTUP_MESSAGE", 0x6f, "B", ["startup_message"])
SerialError = message(DIR_IN, "SERIAL_ERROR", 0xae, None, ["error_number", "msg_contents"])
RecvBroadcastData = message(DIR_IN, "RECV_BROADCAST_DATA", 0x4e, "B8s", ["channel_number", "data"])
RecvAcknowledgedData = message(DIR_IN, "RECV_ACKNOWLEDGED_DATA", 0x4f, "B8s", ["channel_number", "data"])
RecvBurstTransferPacket = message(DIR_IN, "RECV_BURST_TRANSFER_PACKET", 0x50, "B8s", ["channel_number", "data"])
ChannelEvent = message(DIR_IN, "CHANNEL_EVENT", 0x40, "BBB", ["channel_number", "msg_id", "msg_code"])
ChannelStatus = message(DIR_IN, "CHANNEL_STATUS", 0x52, "BB", ["channel_number", "channel_status"])
ChannelId = message(DIR_IN, "CHANNEL_ID", 0x51, "BHBB", ["channel_number", "device_number", "device_type_id", "man_id"])
AntVersion = message(DIR_IN, "VERSION", 0x3e, "11s", ["ant_version"])
Capabilities = message(DIR_IN, "CAPABILITIES", 0x54, "BBBBBx", ["max_channels", "max_networks", "standard_opts", "advanced_opts1", "advanced_opts2"])
SerialNumber = message(DIR_IN, "SERIAL_NUMBER", 0x61, "I", ["serial_number"])
# Synthetic Commands
ReadBroadcastData = message(DIR_OUT, "READ_BROADCAST_DATA", None, None, ["channel_number"], matcher=recv_broadcast_matcher)
UnimplementedCommand = message(None, "UNIMPLEMENTED_COMMAND", None, None, ["msg_id", "msg_contents"])

ALL_ANT_COMMANDS = [ UnassignChannel, AssignChannel, SetChannelId, SetChannelPeriod, SetChannelSearchTimeout,
                     SetChannelRfFreq, SetNetworkKey, ResetSystem, OpenChannel, CloseChannel, RequestMessage,
                     SetSearchWaveform, SendBroadcastData, SendAcknowledgedData, SendBurstTransferPacket,
                     StartupMessage, SerialError, RecvBroadcastData, RecvAcknowledgedData, RecvBurstTransferPacket,
                     ChannelEvent, ChannelStatus, ChannelId, AntVersion, Capabilities, SerialNumber ]


class SendBurstData(SendBurstTransferPacket):

    data = None
    channel_number = None

    def __init__(self, channel_number, data):
        if len(data) <= 8: channel_number |= 0x80
        super(SendBurstData, self).__init__(channel_number, data)

    @property
    def done(self):
        return self._done

    @done.setter
    def done(self, value):
        self._done = value
        self.seq_num = 0
        self.index = 0
        self.incr_packet_index()

    def create_next_packet(self):
        """
        Return a command which can be exceuted
        to deliver the next packet of this burst.
        """
        is_last_packet = self.index + 8 >= len(self.data)
        data = self.data[self.index:self.index + 8]
        channel_number = self.channel_number | ((self.seq_num & 0x03) << 5) | (0x80 if is_last_packet else 0x00)
        return SendBurstTransferPacket(channel_number, data)
    
    def incr_packet_index(self):
        """
        Increment the pointer for data in next packet.
        create_next_packet() will update index until
        this method is called.
        """
        self.seq_num += 1
        self.index += 8
        self.has_more_data = self.index < len(self.data)

    def __str__(self):
        return "SEND_BURST_COMMAND(channel_number=%d)" % self.channel_number


class Core(object):
    """
    Asynchronous ANT api.
    """
    
    def __init__(self, hardware, messages=ALL_ANT_COMMANDS):
        self.hardware = hardware
        self.input_msg_by_id = dict((m.ID, m) for m in messages if m.DIRECTION == DIR_IN)
        # per ant protocol doc, writing 15 zeros
        # should reset internal state of device.
        #self.hardware.write([0] * 15, 100)

    def pack(self, command):
        """
        Return an array of byte representing
        the data which needs to be written to
        hardware to execute the given command.
        """
        if command.ID is not None:
            if command.DIRECTION != DIR_OUT:
                _LOG.warning("Request to pack input message. %s", command)
            msg = [SYNC, command.pack_size(), command.ID]
            msg_args = command.pack_args()
            if msg_args is not None:
                msg.extend(array.array("B", msg_args))
                msg.append(generate_checksum(msg))
                return msg
    
    def unpack(self, msg):
        """
        Return the command represented by
        the given byte ANT array.
        """
        if not validate_checksum(msg):
            _LOG.error("Invalid checksum, mesage discarded. %s", msg_to_string(msg))
            return None
        sync, length, msg_id = msg[:3]
        try:
            command_class = self.input_msg_by_id[msg_id]
        except (KeyError):
            _LOG.warning("Attempt to unpack unkown message (0x%02x). %s", msg_id, msg_to_string(msg))
            return UnimplementedCommand(msg_id, msg)
        else:
            return command_class.unpack_args(array.array("B", msg[3:-1]).tostring())

    def send(self, command, timeout=100):
        """
        Execute the given command. Retruns true
        if command was written to device. False
        if the device nack'd the write. When
        the method returns false, caller should
        retry.
        """
        msg = self.pack(command)
        if not msg: return True
        _LOG.debug("SEND: %s", msg_to_string(msg))
        # ant protocol states \x00\x00 padding is optiontal
        # but nRF24AP2 seems to occaionally not reply to
        # commands when zero padding is excluded.
        msg.extend([0] * 2)
        try:
            self.hardware.write(msg, timeout)
            return True
        except IOError as (err, msg):
            if err == errno.ETIMEDOUT: return False
            else: raise

    def recv(self, timeout=500):
        """
        A generator which return commands
        parsed from input stream of ant device.
        StopIteration raised when input stream empty.
        """
        while True:
            try:
                # tokenize message (possibly more than on per read)
                for msg in tokenize_message(self.hardware.read(timeout)):
                    _LOG.debug("RECV: %s", msg_to_string(msg))
                    cmd = self.unpack(msg)
                    if cmd: yield cmd
            except IOError as (err, msg):
                # iteration terminates on timeout
                if err == errno.ETIMEDOUT: raise StopIteration()
                else: raise


class Session(object):
    """
    Provides synchrous (blocking) API
    on top of basic (Core) ANT impl.
    """

    channels = []
    networks = []

    def __init__(self, core, open=True):
        self.core = core
        self.running = False
        self.running_cmd = None
        try:
            if open: self.open()
        except Exception:
            try: self.close()
            except Exception: _LOG.warning("Caught exception trying to cleanup resources.", exc_info=True)
            finally: raise
            
    
    def open(self):
        """
        Start the message consumer thread.
        """
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self.loop)
            self.thread.daemon = True
            self.thread.start()
            self.reset_system()

    def close(self):
        """
        Stop the message consumer thread.
        """
        try:
            self.reset_system()
            self.running = False
            self.thread.join(1)
            assert not self.thread.is_alive()
        except AttributeError: pass

    def reset_system(self):
        """
        Reset the and device and initialize
        channel/network properties.
        """
        self._send(ResetSystem(), timeout=.5, retry=5)
        if not self.channels:
            cap = self.get_capabilities() 
            ver = self.get_ant_version()
            sn = self.get_serial_number()
            _LOG.debug("Device Capabilities: %s", cap)
            _LOG.debug("Device ANT Version: %s", ver)
            _LOG.debug("Device SN#: %s", sn)
            self.channels = [Channel(self, n) for n in range(0, cap.max_channels)]
            self.networks = [Network(self, n) for n in range(0, cap.max_networks)]

    def get_capabilities(self):
        """
        Return the capabilities of this device. 9.5.7.4
        """
        return self._send(RequestMessage(0, Capabilities.ID))

    def get_ant_version(self):
        """
        Return the version on ANT firmware on device. 9.5.7.3
        """
        return self._send(RequestMessage(0, AntVersion.ID))

    def get_serial_number(self):
        """
        Return SN# of and device. 9.5.7.5
        """
        return self._send(RequestMessage(0, SerialNumber.ID))

    def _send(self, cmd, timeout=1, retry=0):
        """
        Execute the given command. An exception will
        be raised if reply is not received in timeout
        seconds. If retry is non-zero, commands returning
        EAGAIN will be retried. retry also appleis to
        RESET_SYSTEM commands. This method blocks until
        a repsonse if received from hardware or timeout.
        Care should be taken to ensure timeout is sufficiently
        large. Care should be taken to ensure timeout is
        at-least as large a on message period.
        """
        _LOG.debug("Executing Command. %s", cmd)
        for t in range(0, retry + 1):
            # invalid to send command while another is running
            # (execpt for reset system)
            assert not self.running_cmd or isinstance(cmd, ResetSystem)
            # set expiration and event on command. Once self.runnning_cmd
            # is set access to this command from this tread is invalid 
            # until event object is set.
            cmd.expiration = time.time() + timeout if timeout > 0 else None
            cmd.done = threading.Event()
            self.running_cmd = cmd
            # continue trying to commit command until session closed or command timeout 
            while self.running and not cmd.done.is_set() and not self.core.send(cmd):
                _LOG.warning("Device write timeout. Will keep trying.")
            # continue waiting for command completion until session closed
            while self.running and not cmd.done.is_set():
                if isinstance(cmd, SendBurstData) and cmd.has_more_data:
                    # if the command being executed is burst
                    # continue writing packets until data empty.
                    # usb will nack packed it case where we're
                    # overflowing the ant device. and packet will
                    # be tring next time.
                    packet = cmd.create_next_packet()
                    if self.core.send(packet): cmd.incr_packet_index()
                else:
                    cmd.done.wait(1)
            # cmd.done guarenetees a result is availible
            if cmd.done.is_set():
                try:
                    return cmd.result
                except AttributeError:
                    # must have failed, theck if error is retryable
                    if t < retry and cmd.is_retryable(cmd.error):
                        _LOG.warning("Retryable error. %d try(s) remaining. %s", retry - t, cmd.error)
                    else:
                        # not retryable, or too many retries
                        raise cmd.error
            else:
                raise IOError(errno.EBADF, "Session closed.")

    def _handle_reply(self, cmd):
        """
        Handle the given command, updating
        the status of running command if
        applicable.
        """
        _LOG.debug("Processing reply. %s", cmd)
        if self.running_cmd and self.running_cmd.is_reply(cmd):
            err = self.running_cmd.validate_reply(cmd)
            if err:
                self._set_error(err)
            else:
                self._set_result(cmd)

    def _handle_timeout(self):
        """
        Update the status of running command
        if the message has expired.
        """
        # if a command is currently running, check for timeout condition
        if self.running_cmd and self.running_cmd.expiration and time.time() > self.running_cmd.expiration:
            self._set_error(IOError(errno.ETIMEDOUT, "No reply to command. %s" %  self.running_cmd))

    def _set_result(self, result):
        """
        Update the running command with given result,
        and set flag to indicate to caller that command
        is done.
        """
        if self.running_cmd:
            self.running_cmd.result = result
            self.running_cmd.done.set()
            self.running_cmd = None

    def _set_error(self, err):
        """
        Update the running command with 
        given exception. The exception will
        be raised to thread which invoked 
        synchronous command.
        """
        if self.running_cmd:
            self.running_cmd.error = err
            self.running_cmd.done.set()
            self.running_cmd = None

    def loop(self):
        """
        Message loop consuming data from the
        ANT device. Typically loop is started
        by thread created in Session.open()
        """
        try:
            while self.running:
                for cmd in self.core.recv():
                    if not self.running: break
                    self._handle_reply(cmd)
                    self._handle_timeout()
                else:
                    if not self.running: break
                    self._handle_timeout()
        except Exception:
            _LOG.error("Caught Exception handling message, session closing.", exc_info=True)
        finally:
            self.running_cmd = None
            self.running = False


class Channel(object):

    def __init__(self, session, channel_number):
        self._session = session;
        self.channel_number = channel_number

    def open(self):
        self._session._send(OpenChannel(self.channel_number))

    def close(self):
        self._session._send(CloseChannel(self.channel_number))

    def assign(self, channel_type, network_number):
        self._session._send(AssignChannel(self.channel_number, channel_type, network_number))

    def unassign(self):
        self._session._send(UnassignChannel(self.channel_number))

    def set_id(self, device_number=0, device_type_id=0, trans_type=0):
        self._session._send(SetChannelId(self.channel_number, device_number, device_type_id, trans_type))

    def set_period(self, messaging_period=8192):
        self._session._send(SetChannelPeriod(self.channel_number, messaging_period))

    def set_search_timeout(self, search_timeout=12):
        self._session._send(SetChannelSearchTimeout(self.channel_number, search_timeout))

    def set_rf_freq(self, rf_freq=66):
        self._session._send(SetChannelRfFreq(self.channel_number, rf_freq))

    def set_search_waveform(self, search_waveform=None):
        if search_waveform is not None:
            self._session._send(SetSearchWaveform(self.channel_number, search_waveform))

    def get_status(self):
        return self._session._send(RequestMessage(self.channel_number, ChannelStatus.ID))

    def get_id(self):
        return self._session._send(RequestMessage(self.channel_number, ChannelId.ID))

    def send_broadcast(self, data, timeout=2):
        data = data_tostring(data)
        assert len(data) <= 8
        self._session._send(SendBroadcastData(self.channel_number, data), timeout=timeout)

    def send_acknowledged(self, data, timeout=2, retry=4):
        data = data_tostring(data)
        assert len(data) <= 8
        self._session._send(SendAcknowledgedData(self.channel_number, data), timeout=timeout, retry=retry)

    def send_burst(self, data, timeout=60, retry=0):
        data = data_tostring(data)
        self._session._send(SendBurstData(self.channel_number, data), timeout=timeout, retry=retry)

    def recv_broadcast(self, timeout=2):
        return self._session._send(ReadBroadcastData(self.channel_number), timeout=timeout).data

    def write(self, data, timeout=60):
        data = data_tostring(data)
        if len(data) <= 8:
            self.send_acknowledged(data, timeout=timeout, retry=4)
        else:
            self.send_burst(data, timeout=timeout, retry=0)


class Network(object):

    def __init__(self, session, network_number):
        self._session = session
        self.network_number = network_number

    def set_key(self, network_key="\x00" * 8):
        self._session._send(SetNetworkKey(self.network_number, network_key))


# vim: ts=4 sts=4 et
