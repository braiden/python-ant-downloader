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

import antagent.ant as ant

_LOG = logging.getLogger("antagant.antfs")

ANTFS_HOST_ID = os.getpid() & 0xFFFFFFFF
ANTFS_HOST_NAME = socket.gethostname()[:8]

ANTFS_BEACON = 0x43
ANTFS_COMMAND = 0x44
ANTFS_LINK = 0x02
ANTFS_DISC = 0x03
ANTFS_AUTH = 0x04
ANTFS_PING = 0x05
ANTFS_DIRECT = 0x0D

ANTFS_BEACON_STATE_LINK = 0
ANTFS_BEACON_STATE_AUTH = 1
ANTFS_BEACON_STATE_TRANSPORT = 2
ANTFS_BEACON_STATE_BUSY = 3

ANTFS_SEARCH_NETWORK_KEY = "\xa8\xa4\x23\xb9\xf5\x5e\x63\xc1"
ANTFS_SEARCH_FREQ = 50
ANTFS_SEARCH_PERIOD = 0x1000
ANTFS_SEARCH_CHANNEL_TIMEOUT = 255
ANTFS_SEARCH_SEARCH_WAVEFORM = 0x0053

ANTFS_TRANSPORT_ACK_RETRY = 4
ANTFS_TRANSPORT_FREQS =  [3 ,7 ,15, 20, 25, 29, 34, 40, 45, 49, 54, 60, 65, 70, 75, 80];
ANTFS_TRANSPORT_PERIOD = 0b100
ANTFS_TRANSPORT_CHANNEL_TIMEOUT = 2

ANTFS_BEACON_FMT = struct.Struct("<BBBBI")
ANTFS_BEACON_ARGS = collections.namedtuple("AntFsBeacon", ["data_page_id", "beacon_channel_period",
                                                           "pairing_enabled", "upload_enabled",
                                                           "data_availible", "device_state",
                                                           "auth_type", "descriptor"])
def unpack_beacon(msg):
    if msg and ord(msg[0]) == ANTFS_BEACON:
        data_page_id, status_1, status_2, auth_type, descriptor = ANTFS_BEACON_FMT.unpack(msg)
        return ANTFS_BEACON_ARGS(data_page_id, 0x07 & status_1, 0x80 & status_1,
                                 0x10 & status_1, 0x20 & status_1, 0x0f & status_2,
                                 auth_type, descriptor)

ANTFS_LINK_FMT = struct.Struct("<BBBBI")
def pack_link(freq):
    return ANTFS_LINK_FMT.pack(ANTFS_COMMAND, ANTFS_LINK, freq, ANTFS_TRANSPORT_PERIOD, ANTFS_HOST_ID)

ANTFS_AUTH_FMT = struct.Struct("<BBBBI")
ANTFS_AUTH_ARGS = collections.namedtuple("AntFsAuth", ["data_page_id", "command_id", "response_type",
                                                       "auth_string_length", "client_id", "auth_string"])
def pack_auth_get_sn():
    return ANTFS_AUTH_FMT.pack(ANTFS_COMMAND, ANTFS_AUTH, 1, 0, ANTFS_HOST_ID)

def unpack_auth_reply(msg):
    beacon = unpack_beacon(msg[:8]) if msg else None
    cmd = msg[8:]
    if cmd and ord(cmd[0]) == ANTFS_COMMAND and ord(cmd[1]) == ANTFS_AUTH | 0x80:
        data_page_id, command_type, response_type, auth_string_length, client_id = ANTFS_AUTH_FMT.unpack(cmd[:8])
        return beacon, ANTFS_AUTH_ARGS(data_page_id, command_type, response_type, auth_string_length, client_id, cmd[8:8 + auth_string_length])
    return None, None

class Host(object):

    def __init__(self, ant_session, known_client_keys=None):
        self.ant_session = ant_session
        self.known_client_keys = known_client_keys or {}

    def search(self, search_timeout=60):
        """
        Return the first device found which has some actionable
        flag. Either it has data for download or is availible for
        pairing. Multiple calls will restart search. If multiple
        devices are in range, and you are searching for a specific
        device, you need to continue executing until the device is
        returned. Each invokation returns randomly the first device
        found. This will behave poorly if too many devices are in 
        range. This operation is passive, and doesn't not impact
        battery on any devices in range. So I could be run as
        part of an infinite loop to auto action devices.
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
                beacon = unpack_beacon(self.channel.recv_broadcast(timeout=timeout - time.time()))
            except ant.AntTimeoutError:
                # ignore timeout error
                pass
            else:
                # check if event was a beacon
                if beacon:
                    _LOG.debug("Got ANT-FS Beacon. %s", beacon)
                    # and if device is a state which will accept our link
                    if  beacon.device_state != ANTFS_BEACON_STATE_LINK:
                        _LOG.warning("Device busy, not ready for link. client_id=%s state=%d.",
                                beacon.descriptor, beacon.device_state)
                    elif not beacon.data_availible and not beacon.pairing_enabled:
                        _LOG.info("Found device, but no new data for download. client_id=%s",
                                beacon.descriptor)
                    else:
                        return beacon
        
    def link(self):
        """
        Atempt to create an ANTFS link with the device
        currently being tracked by this ant host. e.g.
        teh device which was last returned from search.
        """
        # send the link commmand
        freq = random.choice(ANTFS_TRANSPORT_FREQS)
        link_cmd = pack_link(freq)
        self.channel.write(link_cmd)
        # change this channels frequency to match link
        self._configure_antfs_transport_channel(freq)
        # block indefinately for the antfs beacon on new freq.
        # (don't need a timeout since channel will auto close if device lost)
        beacon = unpack_beacon(self.channel.recv_broadcast(0))
        # device should be broadcasting our id and ready to accept auth
        assert beacon.device_state == ANTFS_BEACON_STATE_AUTH and beacon.descriptor == ANTFS_HOST_ID

    def auth(self):
        # get the S/N of client device
        self.channel.write(pack_auth_get_sn())
        while True:
            beacon, sn = unpack_auth_reply(self.channel.read())
            if sn: break
        _LOG.debug("Got client auth string. %s", sn)
        # check if the auth key for this device is known
        key = self.known_client_keys.get(sn.client_id, None)
        if key:
            pass
        elif beacon.pairing_enabled:
            pass
        else:
            _LOG.warning("Device 0x08%x has data but pairing is disabled and key is unkown.", sn.client_id)

    def send_direct(self, msg):
        pass

    def _open_antfs_search_channel(self):
        self.ant_session.open()
        self.ant_session.reset_system()
        self.channel = self.ant_session.channels[0]
        self.network = self.ant_session.networks[0]
        self._configure_antfs_search_channel()
        self.channel.open()

    def _configure_antfs_search_channel(self):
        self.network.set_key(ANTFS_SEARCH_NETWORK_KEY)
        self.channel.assign(channel_type=0x00, network_number=self.network.network_number)
        self.channel.set_id(device_number=0, device_type_id=0, trans_type=0)
        self.channel.set_period(ANTFS_SEARCH_PERIOD)
        self.channel.set_search_timeout(ANTFS_SEARCH_CHANNEL_TIMEOUT)
        self.channel.set_rf_freq(ANTFS_SEARCH_FREQ)
        self.channel.set_search_waveform(ANTFS_SEARCH_SEARCH_WAVEFORM)

    def _configure_antfs_transport_channel(self, freq):
        self.channel.set_rf_freq(freq)
        self.channel.set_search_timeout(ANTFS_TRANSPORT_CHANNEL_TIMEOUT)
        period_hz = 2 ** (ANTFS_TRANSPORT_PERIOD - 1)
        channel_period = 0x8000 / period_hz
        self.channel.set_period(channel_period)


# vim: ts=4 sts=4 et
