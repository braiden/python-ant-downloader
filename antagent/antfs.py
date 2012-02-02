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

import antagent.ant as ant

_LOG = logging.getLogger("antagant.antfs")

ANTFS_HOST_ID = os.getpid() & 0xFFFF

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
ANTFS_BEACON_ARGS = collections.namedtuple("AntFsBeacon", ["data_page_id", "status_1", "status_2", "auth_type", "descriptor"])
def unpack_beacon(msg):
    if msg and ord(msg[0]) == ANTFS_BEACON:
        return ANTFS_BEACON_ARGS(*ANTFS_BEACON_FMT.unpack(msg))

ANTFS_LINK_FMT = struct.Struct("<BBBBI")
def pack_antfs_link(freq):
    return ANTFS_LINK_FMT.pack(ANTFS_COMMAND, ANTFS_LINK, freq, ANTFS_TRANSPORT_PERIOD, ANTFS_HOST_ID)

class Host(object):

    def __init__(self, ant_session):
        self.ant_session = ant_session

    def link(self, search_timeout=60):
        self._open_antfs_search_channel()
        timeout = time.time() + search_timeout
        try:
            while time.time() < timeout:
                try:
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
                        if  beacon.status_2 & 0x0F != ANTFS_BEACON_STATE_LINK:
                            _LOG.debug("Device busy, not ready for link, state=%d.", beacon.status_2 & 0x0F)
                        else:
                            break
            # send the link commmand
            freq = random.choice(ANTFS_TRANSPORT_FREQS)
            link_cmd = pack_antfs_link(freq)
            self.channel.write(link_cmd)
            # change this channels frequency to match link
            self._configure_antfs_transport_channel(freq)
            # block indefinately for the antfs beacon on new freq.
            # (don't need a timeout since channel will auto close if device lost)
            beacon = unpack_beacon(self.channel.recv_broadcast(0))
            # device should be broadcasting our id and ready to accept auth
            assert beacon.status_2 & 0x0F == ANTFS_BEACON_STATE_AUTH and beacon.descriptor == ANTFS_HOST_ID
        except Exception:
            try: self.ant_session.reset_system()
            except Exception: _LOG.warning("Caught exception trying to cleanup.", exc_info=True)
            raise

    def auth(self, client_keys):
        pass

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
