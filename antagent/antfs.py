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


_LOG = logging.getLogger("antagant.antfs")

ANTFS_BEACON = 0x43
ANTFS_COMMAND = 0x44

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

ANTFS_BEACON_FMT = struct.Struct("<BBBBH")
ANTFS_BEACON_ARGS = collections.namedtuple("AntFsBeacon", ["data_page_id", "status_1", "status_2", "auth_type" "descriptor"])

def unpack_antfs_beacon(msg):
    if msg and msg[0] == ANTFS_BEACON:
        return ANTFS_BEACON_ARGS(*ANTFS_BEACON_FMT.unpack(msg))

class AntFsHost(object):

    def __init__(self, ant_session)
        self.ant_session = ant_session
        if open: self.open()

    def link(self, search_timeout=60):
        try:
            while True:
                beacon = unpack_antfs_beacon(self.channel.recv_broadcast(timeout=search_timeout))
                if beacon:
                    _LOG.debug("Got ANT-FS Beacon. %s", beacon)
                    if  beacon.status_1 & 0x0F != ANTFS_BEACON_STATE_LINK:
                        _LOG.debug("Device busy, not ready for link, state=%d.", beacon.status_1 & 0x0F)
                    else:
                        break
                
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
