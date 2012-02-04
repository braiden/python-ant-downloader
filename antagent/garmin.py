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


import logging
import struct
import time

import antagent.ant as ant

_log = logging.getLogger("antagent.garmin")

class P000(object):
    PID_ACK = 6
    PID_NACK = 21

class L000(P000):
    PID_PROTOCOL_ARRAY = 253
    PID_PRODUCT_RQST = 254
    PID_PRODUCT_DATA = 255
    PID_EXT_PRODUCT_DATA = 248

class L001(L000):
    PID_COMMAND_DATA = 10                  
    PID_XFER_CMPLT = 12
    PID_DATE_TIME_DATA = 14
    PID_POSITION_DATA = 17
    PID_PRX_WPT_DATA = 19
    PID_RECORDS = 27
    PID_RTE_HDR = 29
    PID_RTE_WPT_DATA = 30
    PID_ALMANAC_DATA = 31
    PID_TRK_DATA = 34
    PID_WPT_DATA = 35
    PID_PVT_DATA = 51
    PID_RTE_LINK_DATA = 98
    PID_TRK_HDR = 99
    PID_FLIGHTBOOK_RECORD = 134
    PID_LAP = 149
    PID_WPT_CAT = 152
    PID_RUN = 990
    PID_WORKOUT = 991
    PID_WORKOUT_OCCURRENCE = 992
    PID_FITNESS_USER_PROFILE = 993
    PID_WORKOUT_LIMITS = 994
    PID_COURSE = 1061
    PID_COURSE_LAP = 1062
    PID_COURSE_POINT = 1063
    PID_COURSE_TRK_HDR = 1064
    PID_COURSE_TRK_DATA = 1065
    PID_COURSE_LIMITS = 1066      


def pack(pid, data_type=None):
    return struct.pack("<HHHxx", pid, 0 if data_type is None else 2, data_type or 0)

def unpack(msg):
    pid, length = struct.unpack("<HH", msg[:4])
    data = msg[4:4 + length]
    return pid, data

class Device(object):

    def __init__(self, stream):
        self.stream = stream

    def _execute(self, request):
        in_packets = []
        self.stream.write(pack(*request))
        while True:
            result = self.stream.read()
            if not result: break
            pid, data = unpack(result)
            in_packets.append(result)
            # attempt to ack packet, when the 405cx bezzle is locked
            # it sometimes dispayes "bezzle locked" message to user
            # and drops the radio?! in order to continue commuciation
            # the channel needs to re track. so we wait a long time
            # when retrying ACK transmission. This probably usually
            # only shows up at start of session.
            for n in range(0, 10):
                try: self.stream.write(pack(P000.PID_ACK, pid))
                except ant.AntTxFailedError:
                    _log.warning("Device rejected ACK packet, sleeping before retry.")
                    time.sleep(1)
                else: break
            else:
                raise ant.AntTimeoutError()
        return in_packets

# vim: ts=4 sts=4 et
