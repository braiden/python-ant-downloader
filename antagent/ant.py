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
# command category
TYPE_CONFIG = "CONFIG"
TYPE_NOTIFICATION = "NOTIFICATION"
TYPE_CONTROL = "CONTROL"
TYPE_DATA = "DATA"
TYPE_CHANNEL_EVENT = "CHANNEL_EVENT"
TYPE_REPLY = "REPLY"
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

def is_same_channel(request, response):
    """
    Retrun true if the given request and
    reponse command objects share the same
    channel_number, or if response has no
    channel_Number.
    """
    try: response_channel = response.channel_number
    except AttributeError: return True
    try: request_channel = request.channel_number
    except AttributeError: request_channel = -1
    return response_channel == request_channel

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

def timeout_retry_policy(error):
    return isinstance(error, IOError) and error[0] in (errno.EAGAIN or errno.ETIMEDOUT)

def default_retry_policy(error):
    return isinstance(error, IOError) and error[0] == errno.EAGAIN

def always_retry_policy(error):
    return True

def never_retry_policy(error):
    return False

def message(direction, category, name, id, pack_format, arg_names, retry_policy=default_retry_policy):
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
        CATEGORY = category
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
            except NameError: pass

        def pack_args(self):
            try: return msg_struct.pack(*self.args)
            except NameError: pass
        
        def pack_size(self):
            try: return msg_struct.size
            except NameError: return 0

        def is_retryable(self, err):
            return retry_policy(err)

        def __str__(self):
            return str(self.args)

    return Message

# ANT Message Protocol Definitions
UnassignChannel = message(DIR_OUT, TYPE_CONFIG, "UNASSIGN_CHANNEL", 0x41, "B", ["channel_number"], retry_policy=timeout_retry_policy)
AssignChannel = message(DIR_OUT, TYPE_CONFIG, "ASSIGN_CHANNEL", 0x42, "BBB", ["channel_number", "channel_type", "network_number"], retry_policy=timeout_retry_policy)
SetChannelId = message(DIR_OUT, TYPE_CONFIG, "SET_CHANNEL_ID", 0x51, "BHBB", ["channel_number", "device_number", "device_type_id", "trans_type"], retry_policy=timeout_retry_policy)
SetChannelPeriod = message(DIR_OUT, TYPE_CONFIG, "SET_CHANNEL_PERIOD", 0x43, "BH", ["channel_number", "messaging_period"], retry_policy=timeout_retry_policy) 
SetChannelSearchTimeout = message(DIR_OUT, TYPE_CONFIG, "SET_CHANNEL_SEARCH_TIMEOUT", 0x44, "BB", ["channel_number", "search_timeout"], retry_policy=timeout_retry_policy)
SetChannelRfFreq = message(DIR_OUT, TYPE_CONFIG, "SET_CHANNEL_RF_FREQ", 0x45, "BB", ["channel_number", "rf_freq"], retry_policy=timeout_retry_policy)
SetNetworkKey = message(DIR_OUT, TYPE_CONFIG, "SET_NETWORK_KEY", 0x46, "B8s", ["network_number", "network_key"], retry_policy=timeout_retry_policy)
ResetSystem = message(DIR_OUT, TYPE_CONTROL, "RESET_SYSTEM", 0x4a, "x", [], retry_policy=always_retry_policy)
OpenChannel = message(DIR_OUT, TYPE_CONTROL, "OPEN_CHANNEL", 0x4b, "B", ["channel_number"], retry_policy=timeout_retry_policy)
CloseChannel = message(DIR_OUT, TYPE_CONTROL, "CLOSE_CHANNEL", 0x4c, "B", ["channel_number"], retry_policy=timeout_retry_policy)
RequestMessage = message(DIR_OUT, TYPE_CONTROL, "REQUEST_MESSAGE", 0x4d, "BB", ["channel_number", "msg_id"], retry_policy=timeout_retry_policy)
SetSearchWaveform = message(DIR_OUT, TYPE_CONTROL, "SET_SEARCH_WAVEFORM", 0x49, "BH", ["channel_number", "waveform"], retry_policy=timeout_retry_policy)
SendBroadcastData = message(DIR_OUT, TYPE_DATA, "SEND_BROADCAST_DATA", 0x4e, "B8s", ["channel_number", "data"])
SendAcknowledgedData = message(DIR_OUT, TYPE_DATA, "SEND_ACKNOWLEDGED_DATA", 0x4f, "B8s", ["channel_number", "data"])
SendBurstTransferPacket = message(DIR_OUT, TYPE_DATA, "SEND_BURST_TRANSFER_PACKET", 0x50, "B8s", ["channel_number", "data"])
StartupMessage = message(DIR_IN, TYPE_NOTIFICATION, "STARTUP_MESSAGE", 0x6f, "B", ["startup_message"])
SerialError = message(DIR_IN, TYPE_NOTIFICATION, "SERIAL_ERROR", 0xae, None, ["error_number", "msg_contents"])
RecvBroadcastData = message(DIR_IN, TYPE_DATA, "RECV_BROADCAST_DATA", 0x4e, "B8s", ["channel_number", "data"])
RecvAcknowledgedData = message(DIR_IN, TYPE_DATA, "RECV_ACKNOWLEDGED_DATA", 0x4f, "B8s", ["channel_number", "data"])
RecvBurstTransferPacket = message(DIR_IN, TYPE_DATA, "RECV_BURST_TRANSFER_PACKET", 0x50, "B8s", ["channel_number", "data"])
ChannelEvent = message(DIR_IN, TYPE_CHANNEL_EVENT, "CHANNEL_EVENT", 0x40, "BBB", ["channel_number", "msg_id", "msg_code"])
ChannelStatus = message(DIR_IN, TYPE_REPLY, "CHANNEL_STATUS", 0x52, "BB", ["channel_number", "channel_status"])
ChannelId = message(DIR_IN, TYPE_REPLY, "CHANNEL_ID", 0x51, "BHBB", ["channel_number", "device_number", "device_type_id", "man_id"])
AntVersion = message(DIR_IN, TYPE_REPLY, "VERSION", 0x3e, "11s", ["ant_version"])
Capabilities = message(DIR_IN, TYPE_REPLY, "CAPABILITIES", 0x54, "BBBBBx", ["max_channels", "max_networks", "standard_opts", "advanced_opts1", "advanced_opts2"])
SerialNumber = message(DIR_IN, TYPE_REPLY, "SERIAL_NUMBER", 0x61, "4s", ["serial_number"])
# Synthetic Commands
ReadBroadcastData = message(DIR_OUT, TYPE_DATA, "READ_BROADCAST_DATA", None, None, ["channel_number"])
UnimplementedCommand = message(None, None, "UNIMPLEMENTED_COMMAND", None, None, ["msg_id", "msg_contents"])
SendBurstCommand = message(DIR_OUT, TYPE_DATA, "SEND_BURST_COMMAND", None, None, ["channel_number", "data"])

ALL_ANT_COMMANDS = [ UnassignChannel, AssignChannel, SetChannelId, SetChannelPeriod, SetChannelSearchTimeout,
                     SetChannelRfFreq, SetNetworkKey, ResetSystem, OpenChannel, CloseChannel, RequestMessage,
                     SetSearchWaveform, SendBroadcastData, SendAcknowledgedData, SendBurstTransferPacket,
                     StartupMessage, SerialError, RecvBroadcastData, RecvAcknowledgedData, RecvBurstTransferPacket,
                     ChannelEvent, ChannelStatus, ChannelId, AntVersion, Capabilities, SerialNumber ]


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
            if command.DIRECTION == DIR_IN:
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
        cap = self.get_capabilities() 
        ver = self.get_ant_version()
        sn = self.get_serial_number()
        _LOG.debug("Device Capabilities: %s", cap)
        _LOG.debug("Device ANT Version: %s", ver)
        _LOG.debug("Device SN#: %s", sn)
        if not self.channels:
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
            cmd.expiration = time.time() + timeout
            cmd.done = threading.Event()
            self.running_cmd = cmd
            # continue trying to commit command until session closed or command timeout 
            while self.running and not cmd.done.is_set() and not self.core.send(cmd):
                _LOG.warning("Device write timeout. Will keep trying.")
            # continue waiting for command completion until session closed
            while self.running and not cmd.done.is_set():
                if isinstance(cmd, SendBurstCommand) and not cmd.has_more_data:
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
        # FIXME, need to refactor lost of these if's into Message class strategies.
        _LOG.debug("Processing reply. %s", cmd)
        if self.running_cmd and isinstance(self.running_cmd, SetNetworkKey) \
                and isinstance(cmd, ChannelEvent) \
                and cmd.channel_number == self.running_cmd.network_number:
            # reply to set network key
            if cmd.msg_code != RESPONSE_NO_ERROR:
                # command failed
                error_invalid_usage = IOError(errno.EINVAL, "Failed to execute command message_code=%d. %s" % (cmd.msg_code, self.running_cmd))
                self._set_error(error_invalid_usage)
            else:
                # command succeeded
                self._set_result(cmd)
        elif self.running_cmd and is_same_channel(self.running_cmd, cmd):
            if isinstance(self.running_cmd, RequestMessage) \
                    and self.running_cmd.msg_id == cmd.ID:
                # running command is REQUEST_MESSAGE, return reply.
                # no validation is necessary.
                self._set_result(cmd)
            elif isinstance(self.running_cmd,  CloseChannel) \
                    and isinstance(cmd, ChannelEvent) \
                    and cmd.msg_id == 1 \
                    and cmd.msg_code == EVENT_CHANNEL_CLOSED:
                # channel closed, return event.
                # no validation necessary.
                self._set_result(cmd)
            elif isinstance(self.running_cmd, SendBroadcastData) \
                    and isinstance(cmd, ChannelEvent) \
                    and cmd.msg_id == 1 \
                    and cmd.msg_code == EVENT_TX:
                # broadcast complete
                self._set_result(cmd)
            elif isinstance(self.running_cmd, SendAcknowledgedData) or isinstance(self.running_cmd, SendBurstTransferPacket) \
                    and isinstance(cmd, ChannelEvent) \
                    and cmd.args.msg_id == 1:
                # burst of ack message completed
                if cmd.msg_code == EVENT_TRANSFER_TX_COMPLETED:
                    self._set_result(cmd)
                elif cmd.msg_code == EVENT_TRANSFER_TX_FAILED:
                    self._set_error(IOError(errno.EAGAIN, "Acknowledgement not recieved for burst or acknowledged transfer."))
                else:
                    error_invalid_usage = IOError(errno.EINVAL, "Failed to execute command message_code=%d. %s" % (cmd.args.msg_code, self.running_cmd))
                    self._set_error(error_invalid_usage)
            elif isinstance(cmd, ChannelEvent) \
                    and cmd.msg_id == self.running_cmd.ID \
                    and not isinstance(self.running_cmd, CloseChannel):
                # incoming command is channel event matching
                # the currently running command.
                if cmd.msg_code != RESPONSE_NO_ERROR:
                    # command failed
                    error_invalid_usage = IOError(errno.EINVAL, "Failed to execute command message_code=%d. %s" % (cmd.args.msg_code, self.running_cmd))
                    self._set_error(error_invalid_usage)
                else:
                    # command succeeded
                    self._set_result(cmd)
            elif isinstance(cmd, StartupMessage) and isinstance(self.running_cmd, ResetSystem):
                # reset, return reply. FIXME, STARTUP MESSAGE
                # not implemented by older ANT hardware
                self._set_result(cmd)

    def _handle_data(self, cmd):
        """
        Append incoming ack / burst to the
        serial read buffer.
        """
        if self.running_cmd and is_same_channel(self.running_cmd, cmd) \
                and isinstance(self.running_cmd, ReadBroadcastData) \
                and isinstance(cmd, RecvBroadcastData):
            self._set_result(cmd)

    def _handle_timeout(self):
        """
        Update the status of running command
        if the message has expired.
        """
        # if a command is currently running, check for timeout condition
        if self.running_cmd and time.time() > self.running_cmd.expiration:
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
                    self._handle_data(cmd)
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

    def set_search_timeout(self, search_timeout=255):
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

    def send_burst_packet(self, data):
        data = data_tostring(data)
        assert len(data) <= 8
        while not self._session.core.send(SendBurstTransferPacket(self.channel_number, data)): pass

    def read_broadcast(self, timeout=2):
        return self._session._send(ReadBroadcastData(self.channel_number), timeout=timeout).data

#    def write(self, data, timeout=2):
#        data = data_tostring(data)
#        if len(data) <= 8:
#            self.send_acknowledged(data, timeout=timeout, retry=4)
#        else:
#            self._session._send(SendBurstCommand(self.channel_number, data), timeout=timeout, retry=0)


class Network(object):

    def __init__(self, session, network_number):
        self._session = session
        self.network_number = network_number

    def set_key(self, network_key="\x00" * 8):
        self._session._send(SetNetworkKey(self.network_number, network_key))


# vim: ts=4 sts=4 et
