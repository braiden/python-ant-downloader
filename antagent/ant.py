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

import antagent.antmsg as antmsg

_LOG = logging.getLogger("antagent.ant")

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
        assert msg[0] & 0xFE == antmsg.SYNC
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
    try: response_channel = response.args.channel_number
    except AttributeError: return True
    try: request_channel = request.args.channel_number
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

class Command(object):
    """
    A command represent both a Message (antmsg)
    and its arguments.
    """

    def __init__(self, msg, *args, **kwds):
        self.msg = msg
        try:
            self.args = msg.msg_tuple(*args, **kwds)
        except AttributeError:
            self.args = args

    def __str__(self):
        return str(self.args)


class SendBurstCommand(Command):
    """
    A command to iniate a burst output.
    Executing the command only causes
    the frist packet to be sent.
    create_next_packet(), incr_packet_index()
    can be used to create the additional
    commands required to complete the burst.
    """
    
    def __init__(self, channel_number, data):
        super(SendBurstCommand, self).__init__(antmsg.SEND_BURST_TRANSFER_PACKET, channel_number, data)
        self.channel_number = channel_number
        self.data = data
        self.seq_num = 0
        self.index = 0
        self.sent_last_packet = False

    def __str__(self):
        return "BURST_COMMAND(channel_number=%s)" % self.channel_number

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
        return Command(antmsg.SEND_BURST_TRANSFER_PACKET, channel_number, data)
    
    def incr_packet_index(self):
        """
        Increment the pointer for data in next packet.
        create_next_packet() will update index until
        this method is called.
        """
        self.seq_num += 1
        self.index += 8
        self.has_more_data = self.index < len(self.data)


class Core(object):
    """
    Asynchronous ANT api.
    """
    
    def __init__(self, hardware, messages=antmsg.ALL_MESSAGES):
        self.hardware = hardware
        self.input_msg_by_id = dict((m.msg_id, m) for m in messages if m.msg_dir == antmsg.DIR_IN)
        # per ant protocol doc, writing 15 zeros
        # should reset internal state of device.
        #self.hardware.write([0] * 15, 100)

    def pack(self, command):
        """
        Return an array of byte representing
        the data which needs to be written to
        hardware to execute the given command.
        """
        if command.msg.msg_id is None:
            return []
        elif command.msg.msg_dir == antmsg.DIR_IN:
            _LOG.warning("Request to pack input message. %s", command)
        try:
            struct = command.msg.msg_struct
        except AttributeError:
            _LOG.warning("Attempt to pack unsupported command. %s", command)
            return []
        else:
            msg = [antmsg.SYNC, struct.size, command.msg.msg_id]
            msg.extend(array.array("B", struct.pack(*command.args)))
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
            msg_type = self.input_msg_by_id[msg_id]
            struct = msg_type.msg_struct
        except (KeyError, AttributeError):
            _LOG.warning("Attempt to unpack unkown message (0x%02x). %s", msg_id, msg_to_string(msg))
            return Command(msg_id)
        else:
            msg_args = struct.unpack(array.array("B", msg[3:-1]).tostring())
            return Command(msg_type, *msg_args)

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

    def __init__(self, core, start=True):
        self.core = core
        self.running = False
        self.running_cmd = None
        if start: self.start()
    
    def start(self):
        """
        Start the message consumer thread.
        """
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self.loop)
            self.thread.daemon = True
            self.thread.start()
            self.reset_system()

    def stop(self):
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
        self._send(Command(antmsg.RESET_SYSTEM), timeout=.5, retry=5)
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
        return self._send(Command(antmsg.REQUEST_MESSAGE, 0, antmsg.CAPABILITIES.msg_id)).args

    def get_ant_version(self):
        """
        Return the version on ANT firmware on device. 9.5.7.3
        """
        return self._send(Command(antmsg.REQUEST_MESSAGE, 0, antmsg.ANT_VERSION.msg_id)).args

    def get_serial_number(self):
        """
        Return SN# of and device. 9.5.7.5
        """
        return self._send(Command(antmsg.REQUEST_MESSAGE, 0, antmsg.SERIAL_NUMBER.msg_id)).args

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
            assert not self.running_cmd
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
                    if t < retry and cmd.error[0] == errno.EAGAIN \
                            or (cmd.error[0] == errno.ETIMEDOUT and cmd.msg == antmsg.RESET_SYSTEM):
                        _LOG.warning("Retryable error. %d try(s) remaining. %s", retry - t, cmd.error)
                    else:
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
        if self.running_cmd and self.running_cmd.msg == antmsg.SET_NETWORK_KEY \
                and cmd.msg == antmsg.CHANNEL_EVENT \
                and cmd.args.channel_number == self.running_cmd.args.network_number:
            # reply to set network key
            if cmd.args.msg_code != antmsg.RESPONSE_NO_ERROR:
                # command failed
                error_invalid_usage = IOError(errno.EINVAL, "Failed to execute command message_code=%d. %s" % (cmd.args.msg_code, self.running_cmd))
                self._set_error(error_invalid_usage)
            else:
                # command succeeded
                self._set_result(cmd)
        elif self.running_cmd and is_same_channel(self.running_cmd, cmd):
            if self.running_cmd.msg == antmsg.REQUEST_MESSAGE \
                    and self.running_cmd.args.msg_id == cmd.msg.msg_id:
                # running command is REQUEST_MESSAGE, return reply.
                # no validation is necessary.
                self._set_result(cmd)
            elif self.running_cmd.msg == antmsg.CLOSE_CHANNEL \
                    and cmd.msg == antmsg.CHANNEL_EVENT \
                    and cmd.args.msg_id == 1 \
                    and cmd.args.msg_code == antmsg.EVENT_CHANNEL_CLOSED:
                # channel closed, return event.
                # no validation necessary.
                self._set_result(cmd)
            elif self.running_cmd.msg == antmsg.SEND_BROADCAST_DATA \
                    and cmd.args.msg_id == 1 \
                    and cmd.args.msg_code == antmsg.EVENT_TX:
                # broadcast complete
                self._set_result(cmd)
            elif self.running_cmd.msg in (antmsg.SEND_ACKNOWLEDGED_DATA, antmsg.SEND_BURST_TRANSFER_PACKET) \
                    and cmd.args.msg_id == 1:
                # burst of ack message completed
                if cmd.args.msg_code == antmsg.EVENT_TRANSFER_TX_COMPLETED:
                    self._set_result(cmd)
                elif cmd.args.msg_code == antmsg.EVENT_TRANSFER_TX_FAILED:
                    self._set_error(IOError(errno.EAGAIN, "Acknowledgement not recieved for burst or acknowledged transfer."))
                else:
                    error_invalid_usage = IOError(errno.EINVAL, "Failed to execute command message_code=%d. %s" % (cmd.args.msg_code, self.running_cmd))
                    self._set_error(error_invalid_usage)
            elif cmd.msg == antmsg.CHANNEL_EVENT \
                    and cmd.args.msg_id == self.running_cmd.msg.msg_id \
                    and not self.running_cmd.msg == antmsg.CLOSE_CHANNEL:
                # incoming command is channel event matching
                # the currently running command.
                if cmd.args.msg_code != antmsg.RESPONSE_NO_ERROR:
                    # command failed
                    error_invalid_usage = IOError(errno.EINVAL, "Failed to execute command message_code=%d. %s" % (cmd.args.msg_code, self.running_cmd))
                    self._set_error(error_invalid_usage)
                else:
                    # command succeeded
                    self._set_result(cmd)
            elif cmd.msg == antmsg.STARTUP_MESSAGE \
                    and self.running_cmd.msg == antmsg.RESET_SYSTEM:
                # reset, return reply. FIXME, STARTUP MESSAGE
                # not implemented by older ANT hardware
                self._set_result(cmd)
        # check for timeout condition
        self._handle_timeout()

    def _handle_data(self, cmd):
        """
        Append incoming ack / burst to the
        serial read buffer.
        """
        pass

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
        by thread created in Session.start()
        """
        try:
            while self.running:
                for cmd in self.core.recv():
                    if not self.running: break
                    self._handle_reply(cmd)
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

    def open_channel(self):
        self._session._send(Command(antmsg.OPEN_CHANNEL, self.channel_number))

    def close_channel(self):
        self._session._send(Command(antmsg.CLOSE_CHANNEL, self.channel_number))

    def assign_channel(self, channel_type, network_number):
        self._session._send(Command(antmsg.ASSIGN_CHANNEL, self.channel_number, channel_type, network_number))

    def unassign_channel(self):
        self._session._send(Command(antmsg.UNASSIGN_CHANNEL, self.channel_number))

    def set_channel_id(self, device_number=0, device_type_id=0, trans_type=0):
        self._session._send(Command(antmsg.SET_CHANNEL_ID, self.channel_number, device_number, device_type_id, trans_type))

    def set_channel_period(self, messaging_period=8192):
        self._session._send(Command(antmsg.SET_CHANNEL_PERIOD, self.channel_number, messaging_period))

    def set_channel_search_timeout(self, search_timeout=255):
        self._session._send(Command(antmsg.SET_CHANNEL_SEARCH_TIMEOUT, self.channel_number, search_timeout))

    def set_channel_ref_freq(self, rf_freq=66):
        self._session._send(Command(antmsg.SET_CHANNEL_RF_FREQ, self.channel_number, rf_freq))

    def set_channel_search_waveform(self, search_waveform=None):
        if search_waveform is not None:
            self._session._send(Command(antmsg.SET_SEARCH_WAVEFORM, self.channel_number, search_waveform))

    def get_channel_status(self):
        return self._session._send(Command(antmsg.REQUEST_MESSAGE, self.channel_number, antmsg.CHANNEL_STATUS.msg_id)).args

    def get_channel_id(self):
        return self._session._send(Command(antmsg.REQUEST_MESSAGE, self.channel_number, antmsg.CHANNEL_ID.msg_id)).args

    def send_broadcast(self, data, timeout=2):
        data = data_tostring(data)
        assert len(data) <= 8
        self._session._send(Command(antmsg.SEND_BROADCAST_DATA, self.channel_number, data), timeout=timeout)

    def send_acknowledged(self, data, timeout=2, retry=4):
        data = data_tostring(data)
        assert len(data) <= 8
        self._session._send(Command(antmsg.SEND_ACKNOWLEDGED_DATA, self.channel_number, data), timeout=timeout, retry=retry)

    def send_burst_packet(self, data):
        data = data_tostring(data)
        assert len(data) <= 8
        while not self._session.core.send(Command(antmsg.SEND_BURST_TRANSFER_PACKET, self.channel_number, data)): pass

    def read_broadcast(self, timeout=2):
        msg = antmsg.AntMessage(antmsg.DIR_OUT, antmsg.TYPE_DATA, "READ_BROADCAST", None, None, ["channel_number"])
        self._session._send(Command(msg, self.channel_number), timeout=timeout)

    def write(self, data, timeout=2):
        data = data_tostring(data)
        if len(data) <= 8:
            self.send_acknowledged(data, timeout=timeout, retry=4)
        else:
            self._session._send(SendBurstCommand(self.channel_number, data), timeout=timeout, retry=0)


class Network(object):

    def __init__(self, session, network_number):
        self._session = session
        self.network_number = network_number

    def set_network_key(self, network_number=0, network_key="\x00" * 8):
        self._session._send(Command(antmsg.SET_NETWORK_KEY, self.network_number, network_key))


# vim: ts=4 sts=4 et
