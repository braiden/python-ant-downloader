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
    return array.array("B", msg).tostring().encode("hex")

def generate_checksum(msg):
    return reduce(lambda x, y: x ^ y, msg)

def validate_checksum(msg):
    return generate_checksum(msg) == 0

def tokenize_message(msg):
    while msg:
        assert msg[0] & 0xFE == antmsg.SYNC
        length = msg[1]
        yield msg[:4 + length]
        msg = msg[4 + length:]

def is_same_channel(request, response):
    try: response_channel = response.args.channel_number
    except AttributeError: return True
    try: request_channel = request.args.channel_number
    except AttributeError: request_channel = -1
    return response_channel == request_channel


class AntCommand(object):

    def __init__(self, msg, *args, **kwds):
        self.msg = msg
        try:
            self.args = msg.msg_tuple(*args, **kwds)
        except AttributeError:
            self.args = args

    def __str__(self):
        return str(self.args)


class AntCore(object):
    
    def __init__(self, hardware, messages=antmsg.ALL_MESSAGES):
        self.hardware = hardware
        self.input_msg_by_id = dict((m.msg_id, m) for m in messages if m.msg_dir == antmsg.DIR_IN)
        # per ant protocol doc, writing 15 zeros
        # should reset internal state of device.
        #self.hardware.write([0] * 15, 100)

    def pack(self, command):
        if command.msg.msg_id == antmsg.DIR_IN:
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
        if not validate_checksum(msg):
            _LOG.error("Invalid checksum, mesage discarded. %s", msg_to_string(msg))
            return None
        sync, length, msg_id = msg[:3]
        try:
            msg_type = self.input_msg_by_id[msg_id]
            struct = msg_type.msg_struct
        except (KeyError, AttributeError):
            _LOG.warning("Attempt to unpack unkown message (0x%02x). %s", msg_id, msg_to_string(msg))
            return AntCommand(msg_id)
        else:
            msg_args = struct.unpack(array.array("B", msg[3:-1]).tostring())
            return AntCommand(msg_type, *msg_args)

    def send(self, command, timeout=100):
        msg = self.pack(command)
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


class AntSession(object):

    channels = []
    networks = []

    def __init__(self, ant_core, start=True):
        self.ant_core = ant_core
        self.running = False
        self.running_cmd = None
        if start: self.start()
    
    def start(self):
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self.loop)
            self.thread.daemon = True
            self.thread.start()
            self.reset_system()

    def stop(self):
        try:
            self.running = False
            self.thread.join(1)
            assert not self.thread.is_alive()
        except AttributeError: pass

    def reset_system(self):
        self._send(AntCommand(antmsg.RESET_SYSTEM), timeout=.5, retry=5)
        cap = self._send(AntCommand(antmsg.REQUEST_MESSAGE, 0, antmsg.CAPABILITIES.msg_id), retry=1).args
        ver = self._send(AntCommand(antmsg.REQUEST_MESSAGE, 0, antmsg.VERSION.msg_id), retry=1).args
        _LOG.debug("Device Capabilities: %s", cap)
        _LOG.debug("Device ANT Version: %s", ver)
        if not self.channels:
            self.channels = [AntChannel(self, n) for n in range(0, cap.max_channels)]
            self.networks = [AntNetwork(self, n) for n in range(0, cap.max_networks)]

    def _send(self, cmd, timeout=1, retry=0):
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
            while self.running and not cmd.done.is_set() and not self.ant_core.send(cmd):
                _LOG.warning("Device write timeout. Will keep trying.")
            # continue waiting for command completion until session closed
            while self.running and not cmd.done.is_set():
                cmd.done.wait(1)
            # cmd.done guarenetees a result is availible
            if cmd.done.is_set():
                try:
                    return cmd.result
                except AttributeError:
                    if t >= retry:
                        raise cmd.error
                    else:
                        _LOG.warning("Failed to execute command. %d try(s) remaining. %s", retry - t, cmd.error)
            else:
                raise IOError(errno.EBADF, "Session closed.")

    def _handle_reply(self, cmd):
        _LOG.debug("Processing reply. %s", cmd)
        if self.running_cmd and self.running_cmd.msg == antmsg.SET_NETWORK_KEY \
                and cmd.msg == antmsg.CHANNEL_EVENT \
                and cmd.args.channel_number == self.running_cmd.args.network_number:
            # reply to set network key
            if cmd.args.msg_code != antmsg.RESPONSE_NO_ERROR:
                # command failed
                self._set_error(IOError(errno.EINVAL, "Failed to execute command message_code=%d. %s" % (cmd.args.msg_code, self.running_cmd)))
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
            elif cmd.msg == antmsg.CHANNEL_EVENT \
                    and cmd.args.msg_id == self.running_cmd.msg.msg_id:
                # incoming command is channel event matching
                # the currently running command.
                if cmd.args.msg_code != antmsg.RESPONSE_NO_ERROR:
                    # command failed
                    self._set_error(IOError(errno.EINVAL, "Failed to execute command message_code=%d. %s" % (cmd.args.msg_code, self.running_cmd)))
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

    def _handle_timeout(self):
        # if a command is currently running, check for timeout condition
        if self.running_cmd and time.time() > self.running_cmd.expiration:
            self._set_error(IOError(errno.ETIMEDOUT, "No reply to command. %s" %  self.running_cmd))

    def _set_result(self, result):
        if self.running_cmd:
            self.running_cmd.result = result
            self.running_cmd.done.set()
            self.running_cmd = None

    def _set_error(self, err):
        if self.running_cmd:
            self.running_cmd.error = err
            self.running_cmd.done.set()
            self.running_cmd = None

    def loop(self):
        try:
            while self.running:
                for cmd in self.ant_core.recv():
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


class AntChannel(object):

    def __init__(self, session, channel_number):
        self._session = session;
        self.channel_number = channel_number

    def open_channel(self):
        self._session._send(AntCommand(antmsg.OPEN_CHANNEL, self.channel_number), retry=1)

    def close_channel(self):
        self._session._send(AntCommand(antmsg.CLOSE_CHANNEL, self.channel_number), retry=1)

    def assign_channel(self, channel_type=0, network_number=0):
        self._session._send(AntCommand(antmsg.ASSIGN_CHANNEL, self.channel_number, channel_type, network_number), retry=1)

    def unassign_channel(self):
        self._session._send(AntCommand(antmsg.UNASSIGN_CHANNEL, self.channel_number), retry=1)

    def set_channel_id(self, device_number=0, device_type_id=0, trans_type=0):
        self._session._send(AntCommand(antmsg.SET_CHANNEL_ID, self.channel_number, device_number, device_type_id, trans_type), retry=1)

    def set_channel_period(self, messaging_period=8192):
        self._session._send(AntCommand(antmsg.SET_CHANNEL_PERIOD, self.channel_number, messaging_period), retry=1)

    def set_channel_search_timeout(self, search_timeout=255):
        self._session._send(AntCommand(antmsg.SET_CHANNEL_SEARCH_TIMEOUT, self.channel_number, search_timeout), retry=1)

    def set_channel_ref_freq(self, rf_freq=66):
        self._session._send(AntCommand(antmsg.SET_CHANNEL_RF_FREQ, self.channel_number, rf_freq), retry=1)

    def set_channel_search_waveform(self, search_waveform=None):
        if search_waveform is not None:
            self._session._send(AntCommand(antmsg.SET_SEARCH_WAVEFORM, self.channel_number, search_waveform), retry=1)

    def get_channel_status(self):
        return self._session._send(AntCommand(antmsg.REQUEST_MESSAGE, self.channel_number, antmsg.CHANNEL_STATUS.msg_id), retry=1).args

    def get_channel_id(self):
        return self._session._send(AntCommand(antmsg.REQUEST_MESSAGE, self.channel_number, antmsg.CHANNEL_ID.msg_id), retry=1).args


class AntNetwork(object):

    def __init__(self, session, network_number):
        self._session = session
        self.network_number = network_number

    def set_network_key(self, network_number=0, network_key="\x00" * 8):
        self._session._send(AntCommand(antmsg.SET_NETWORK_KEY, self.network_number, network_key), retry=1)


# vim: ts=4 sts=4 et
