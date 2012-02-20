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


import random
import struct
import collections
import logging
import time
import os
import socket
import binascii
import ConfigParser

import antd.ant as ant

_log = logging.getLogger("antd.antfs")

ANTFS_HOST_ID = os.getpid() & 0xFFFFFFFF
ANTFS_HOST_NAME = socket.gethostname()[:8]


class Beacon(object):

    DATA_PAGE_ID = 0x43
    STATE_LINK, STATE_AUTH, STATE_TRANSPORT, STATE_BUSY = range(0,4)

    __struct = struct.Struct("<BBBBI")

    @classmethod
    def unpack(cls, msg):
        if msg and ord(msg[0]) == Beacon.DATA_PAGE_ID:
            result = cls()
            result.data_page_id, result.status_1, result.status_2, result.auth_type, result.descriptor = cls.__struct.unpack(msg[:8])
            result.period = 0x07 & result.status_1
            result.pairing_enabled = 0x80 & result.status_1
            result.upload_enabled = 0x10 & result.status_1
            result.data_availible = 0x20 & result.status_1
            result.device_state = 0x0f & result.status_2
            result.data = msg[8:]
            return result

    def __str__(self):
        return self.__class__.__name__ + str(self.__dict__)


class Command(object):

    DATA_PAGE_ID = 0x44
    LINK, DISCONNECT, AUTH, PING, DIRECT = 0x02, 0x03, 0x04, 0x05, 0x0D

    __struct = struct.Struct("<BB6x")

    @classmethod
    def unpack(cls, msg):
        beacon = Beacon.unpack(msg) 
        if beacon and beacon.data and ord(beacon.data[0]) == Command.DATA_PAGE_ID:
            result = cls()
            result.beacon = beacon
            result.data_page_id, result.command_id = cls.__struct.unpack(beacon.data[:8])
            return result

    def __str__(self):
        return self.__class__.__name__ + str(self.__dict__)


class Disconnect(Command):
    
    COMMAND_ID = Command.DISCONNECT

    __struct = struct.Struct("<BB6x")

    def pack(self):
        return self.__struct.pack(self.DATA_PAGE_ID, self.COMMAND_ID)


class Ping(Command):
    
    COMMAND_ID = Command.PING

    __struct = struct.Struct("<BB6x")

    def pack(self):
        return self.__struct.pack(self.DATA_PAGE_ID, self.COMMAND_ID)


class Link(Command):

    COMMAND_ID = Command.LINK 

    __struct = struct.Struct("<BBBBI")

    def __init__(self, freq, period, host_id=ANTFS_HOST_ID):
        self.frequency = freq
        self.period = period
        self.host_id = host_id

    def pack(self):
        return self.__struct.pack(self.DATA_PAGE_ID, self.COMMAND_ID, self.frequency, self.period, self.host_id)
    

class Auth(Command):

    COMMAND_ID = Command.AUTH

    OP_PASS_THRU, OP_CLIENT_SN, OP_PAIR, OP_PASSKEY = range(0, 4)
    RESPONSE_NA, RESPONSE_ACCEPT, RESPONSE_REJECT = range(0, 3)

    __struct = struct.Struct("<BBBBI")

    def __init__(self, op_id=None, auth_string="", host_id=ANTFS_HOST_ID):
        self.op_id = op_id
        self.auth_string = auth_string
        self.host_id = host_id

    def pack(self):
        return self.__struct.pack(self.DATA_PAGE_ID, self.COMMAND_ID, self.op_id, len(self.auth_string), self.host_id) + self.auth_string
    
    @classmethod
    def unpack(cls, msg):
        auth = super(Auth, cls).unpack(msg)
        if auth and auth.command_id & 0x7F == Auth.COMMAND_ID:
            data_page_id, command_id, auth.response_type, auth_string_length, auth.client_id = cls.__struct.unpack(auth.beacon.data[:8])
            auth.auth_string = auth.beacon.data[8:8 + auth_string_length]
            return auth


class GarminSendDirect(Command):
    
    COMMAND_ID = Command.DIRECT

    __struct = struct.Struct("<BBHHH")

    def __init__(self, data="", fd=0xFFFF, offset=0x0000):
        self.fd = fd
        self.offset = offset
        self.data = data
        self.blocks = (len(data) - 1) // 8

    def pack(self):
        return self.__struct.pack(self.DATA_PAGE_ID, self.COMMAND_ID, self.fd, self.offset, self.blocks) + self.data
    
    @classmethod
    def unpack(cls, msg):
        direct = super(GarminSendDirect, cls).unpack(msg)
        if direct and direct.command_id & 0x7F == GarminSendDirect.COMMAND_ID:
            data_page_id, command_id, direct.fd, direct.offset, direct.blocks = cls.__struct.unpack(direct.beacon.data[:8])
            direct.data = direct.beacon.data[8:8 + 8 * direct.blocks]
            return direct


class KnownDeviceDb(object):

    def __init__(self, file = None):
        self.file = file
        self.key_by_device_id = dict()
        self.device_id_by_ant_device_number = dict()
        self.cfg = ConfigParser.SafeConfigParser()
        if file: self.cfg.read([file])
        for section in self.cfg.sections():
            device_id = int(section, 0)
            try: self.key_by_device_id[device_id] = binascii.unhexlify(self.cfg.get(section, "key"))
            except ConfigParser.NoOptionError: pass
            try: self.device_id_by_ant_device_number[int(self.cfg.get(section, "device_number"), 0)] = device_id
            except ConfigParser.NoOptionError: pass

    def get_key(self, device_id):
        return self.key_by_device_id.get(device_id, None)

    def add_key(self, device_id, key):
        self.add_to_cfg(device_id, "key", key.encode("hex"))

    def get_device_id(self, ant_device_number):
        return self.device_id_by_ant_device_number.get(ant_device_number, None)

    def add_device_id(self, ant_device_number, device_id):
        self.add_to_cfg(device_id, "device_number", hex(ant_device_number))

    def delete_device(self, device_id):
        section = "0x%08x" % device_id 
        try: self.cfg.remove_section(section)
        except ConfigParser.NoSectionError: pass
        else:
            if self.file:
                with open(self.file, "w") as file:
                    self.cfg.write(file)
        
    def add_to_cfg(self, device_id, key, value):
        section = "0x%08x" % device_id 
        try: self.cfg.add_section(section)
        except ConfigParser.DuplicateSectionError: pass
        self.cfg.set(section, key, value)
        if self.file:
            with open(self.file, "w") as file:
                self.cfg.write(file)


class Host(object):

    search_network_key = "\xa8\xa4\x23\xb9\xf5\x5e\x63\xc1"
    search_freq = 50
    search_period = 0x1000
    search_timeout = 255
    search_waveform = 0x0053

    transport_freqs = [3, 7, 15, 20, 25, 29, 34, 40, 45, 49, 54, 60, 65, 70, 75, 80]
    transport_period = 0b100
    transport_timeout = 2

    def __init__(self, ant_session, known_client_keys=None):
        self.ant_session = ant_session
        self.known_client_keys = known_client_keys if known_client_keys is not None else KnownDeviceDb()

    def close(self):
        self.channel.send_acknowledged(Disconnect().pack(), direct=True)
        self.ant_session.close()

    def disconnect(self):
        try:
            beacon = Beacon.unpack(self.channel.recv_broadcast(.5))
        except ant.AntTimeoutError:
            pass
        else:
            self.channel.send_acknowledged(Disconnect().pack(), direct=True)
            self.channel.close()

    def ping(self):
        self.channel.write(Ping().pack())

    def search(self, search_timeout=60, device_id=None, include_unpaired_devices=False, include_devices_with_no_data=False):
        """
        Search for devices. If device_id is None return the first device
        which has data availible. Unless include_unpaired_devices = True
        only devices for which we know secret key will be returned.

        If device_id is non-None, we will continue to search for device who's
        ANT device_id matchers the requested value. If found the device
        is returned regardless of whether it has data or not.
        include_unpaired_devices is ignored when device_id is provided.
        """
        timeout = time.time() + search_timeout
        while time.time() < timeout:
            try:
                # if we didn't find a device, maybe another is in range?
                # restart search every time. Once a device is tracking
                # we don't get any more hits. So, just keep re-openning
                # channel until we find device we're looking for.
                # TODO could implement AP2 filters, but this logic maintains
                # support for older devices.
                self._open_antfs_search_channel()
                # wait to recv beacon from device
                beacon = Beacon.unpack(self.channel.recv_broadcast(timeout=timeout - time.time()))
            except ant.AntTimeoutError:
                # ignore timeout error
                pass
            else:
                tracking_device_number = self.channel.get_id().device_number
                tracking_device_id = self.known_client_keys.get_device_id(tracking_device_number)
                # check if event was a beacon
                if beacon:
                    _log.debug("Got ANT-FS Beacon. device_number=0x%04x %s", tracking_device_number, beacon)
                    # and if device is a state which will accept our link
                    if  beacon.device_state != Beacon.STATE_LINK:
                        _log.warning("Device busy, not ready for link. device_number=0x%04x state=%d.",
                                tracking_device_number, beacon.device_state)
                    # are we looking for a sepcific device
                    if device_id is not None:
                        if device_id == tracking_device_id:
                            # the device exactly matches the one we're looking for
                            self.beacon = beacon
                            self.device_id = tracking_device_id
                            return beacon
                        else:
                            # a specific device id was request, but is not the one
                            # currently linked, try again. FIXME should really implement
                            # AP2 filters
                            _log.debug("Found device, but device_id does not match. 0x%08x != 0x%08x", tracking_device_id or 0, device_id)
                            continue
                    elif not include_unpaired_devices and tracking_device_id is None:
                        # requested not to return unpared devices
                        # but the one linked is unkown.
                        # FIXME add device to AP2 filter and contiue search
                        _log.debug("Found device, but paring not enabled. device_number=0x%04x", tracking_device_number)
                        continue
                    elif not beacon.data_availible and not include_devices_with_no_data:
                        _log.debug("Found device, but no new data for download. device_number=0x%04x", tracking_device_number)
                    else:
                        self.beacon = beacon
                        self.device_id = tracking_device_id # may be None
                        return beacon
        
    def link(self):
        """
        Atempt to create an ANTFS link with the device
        who's beacon was most recently returned by search().
        If this channel is not tracking, the operation will
        block until a device is found, and attempt a link.
        Operation will raise a timeout exception if device
        does not reply in time our if an attempt was made
        to link while channel was not tracking.
        """
        # make sure our message period matches the target
        _log.debug("Setting period to match device, hz=%d",  2 ** (self.beacon.period - 1))
        self._configure_antfs_period(self.beacon.period)
        # send the link commmand
        link = Link(freq=random.choice(self.transport_freqs), period=self.transport_period)
        _log.debug("Linking with device. freq=24%02dmhz", link.frequency)
        self.channel.send_acknowledged(link.pack())
        # change this channels frequency to match link
        self._configure_antfs_transport_channel(link)
        # block indefinately for the antfs beacon on new freq.
        # (don't need a timeout since channel will auto close if device lost)
        self.beacon = Beacon.unpack(self.channel.recv_broadcast(0))
        # device should be broadcasting our id and ready to accept auth
        assert self.beacon.device_state == Beacon.STATE_AUTH
        return self.beacon

    def auth(self, pair=True, timeout=60):
        """
        Attempt to create an authenticated transport
        with the device we are currenly linked. Not
        valid unless device is in link status.
        If a client key is known, transport will be
        openned without user interaction. If key is unkown
        we will attempt to pair with device (which must
        be acknowledged by human on GPS device.)
        If paising is not enabled Auth is impossible.
        Error raised if auth is not successful.
        Timeout only applies user interaction during pairing process.
        """
        # get the S/N of client device
        auth_cmd = Auth(Auth.OP_CLIENT_SN)
        self.channel.write(auth_cmd.pack())
        while True:
            auth_reply = Auth.unpack(self.channel.read())
            if auth_reply: break
        _log.debug("Got client auth string. %s", auth_reply)
        # check if the auth key for this device is known
        client_id = auth_reply.client_id
        # property may not have been set yet if new device
        self.device_id = client_id  
        # look up key
        key = self.known_client_keys.get_key(client_id)
        if key:
            _log.debug("Device secret known.")
            auth_cmd = Auth(Auth.OP_PASSKEY, key)
            self.channel.write(auth_cmd.pack())
            while True:
                auth_reply = Auth.unpack(self.channel.read())
                if auth_reply: break
            if auth_reply.response_type == Auth.RESPONSE_ACCEPT:
                _log.debug("Device accepted key.")
            else:
                _log.warning("Device pairing failed. Removing key from db. Try re-pairing.")
                self.known_client_keys.delete_device(client_id)
        elif pair:
            _log.debug("Device unkown, requesting pairing.")
            auth_cmd = Auth(Auth.OP_PAIR, ANTFS_HOST_NAME)
            self.channel.write(auth_cmd.pack())
            while True:
                auth_reply = Auth.unpack(self.channel.read(timeout))
                if auth_reply: break
            if auth_reply.response_type == Auth.RESPONSE_ACCEPT:
                _log.debug("Device paired. key=%s", auth_reply.auth_string.encode("hex"))
                self.known_client_keys.add_key(client_id, auth_reply.auth_string)
                device_number = self.channel.get_id().device_number
                self.known_client_keys.add_device_id(device_number, client_id)
            else:
                _log.warning("Device pairing failed. Request rejected?")
        else:
            _log.warning("Device 0x08%x has data but pairing is disabled and key is unkown.", client_id)
        #confirm the ANT-FS channel is open
        self.beacon = Beacon.unpack(self.channel.recv_broadcast(0))
        assert self.beacon.device_state == Beacon.STATE_TRANSPORT
        return self.beacon

    def write(self, msg):
        direct_cmd = GarminSendDirect(msg)
        self.channel.write(direct_cmd.pack())

    def read(self):
        direct_reply = GarminSendDirect.unpack(self.channel.read())
        return direct_reply.data if direct_reply else None

    def _open_antfs_search_channel(self):
        self.ant_session.reset_system()
        self.channel = self.ant_session.channels[0]
        self.network = self.ant_session.networks[0]
        self._configure_antfs_search_channel()
        self.channel.open()

    def _configure_antfs_search_channel(self):
        self.network.set_key(self.search_network_key)
        self.channel.assign(channel_type=0x00, network_number=self.network.network_number)
        self.channel.set_id(device_number=0, device_type_id=0, trans_type=0)
        self.channel.set_period(self.search_period)
        self.channel.set_search_timeout(self.search_timeout)
        self.channel.set_rf_freq(self.search_freq)
        self.channel.set_search_waveform(self.search_waveform)

    def _configure_antfs_transport_channel(self, link):
        self.channel.set_rf_freq(link.frequency)
        self.channel.set_search_timeout(self.transport_timeout)
        self._configure_antfs_period(link.period)

    def _configure_antfs_period(self, period):
        period_hz = 2 ** (period - 1)
        channel_period = 0x8000 / period_hz
        self.channel.set_period(channel_period)
        

# vim: ts=4 sts=4 et
