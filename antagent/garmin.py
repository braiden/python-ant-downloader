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
import collections

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

class A010(object):
    CMND_ABORT_TRANSFER = 0   
    CMND_TRANSFER_ALM = 1
    CMND_TRANSFER_POSN = 2
    CMND_TRANSFER_PRX = 3
    CMND_TRANSFER_RTE = 4
    CMND_TRANSFER_TIME = 5
    CMND_TRANSFER_TRK = 6
    CMND_TRANSFER_WPT = 7
    CMND_TURN_OFF_PWR = 8
    CMND_START_PVT_DATA = 49
    CMND_STOP_PVT_DATA = 50
    CMND_FLIGHTBOOK_TRANSFER = 92
    CMND_TRANSFER_LAPS = 117
    CMND_TRANSFER_WPT_CATS = 121
    CMND_TRANSFER_RUNS = 450
    CMND_TRANSFER_WORKOUTS = 451
    CMND_TRANSFER_WORKOUT_OCCURRENCES = 452
    CMND_TRANSFER_FITNESS_USER_PROFILE = 453
    CMND_TRANSFER_WORKOUT_LIMITS = 454
    CMND_TRANSFER_COURSES = 561
    CMND_TRANSFER_COURSE_LAPS = 562
    CMND_TRANSFER_COURSE_POINTS = 563
    CMND_TRANSFER_COURSE_TRACKS = 564
    CMND_TRANSFER_COURSE_LIMITS = 565

def pack(pid, data_type=None):
    return struct.pack("<HHHxx", pid, 0 if data_type is None else 2, data_type or 0)

def unpack(msg):
    pid, length = struct.unpack("<HH", msg[:4])
    data = msg[4:4 + length]
    return pid, length, data

def tokenize(msg):
    while True:
        pid, length, data = unpack(msg)
        if pid or length:
            yield pid, length, msg[4:length + 4] 
            msg = msg[length + 4:]
            if len(msg) < 4: break
        else:
            break

def chunk(l, n):
    for i in xrange(0, len(l), n):
        yield l[i:i+n]


class Device(object):

    def __init__(self, stream):
        self.stream = stream
        self.data_types = {}

    def get_product_data():
        result = execute(self, L000.PID_PRODUCT_RQST)
        product_description = result.by_pid(P000.PID_PRODUCT_DATA)

    def execute(self, command_pid, ushort_data=None):
        in_packets = []
        self.stream.write(pack(command_pid, ushort_data))
        while True:
            result = self.stream.read()
            if not result: break
            for pid, length, data in tokenize(result):
                in_packets.append((pid, length, data))
                self.stream.write(pack(P000.PID_ACK, pid))
        in_packets.append((0, 0, ""))
        return PacketList(in_packets)

    def parse(self, packet):
        pass


class FileDevice(Device):
    
    def __init__(self, file):
        super(FileDevice, self).__init__(file)

    def execute(self, *args, **kwd):
        in_packets = []
        while True:
            header = self.stream.read(4)
            if not header: break
            pid, length = struct.unpack("<HH", header)  
            data = self.stream.read(length)
            in_packets.append((pid, length, data))
            if (pid, length, data) == (0, 0, ""): break
        return PacketList(in_packets)


class PacketList(list):

    def __init__(self, iterable):
        super(PacketList, self).__init__(Packet(*i) for i in iterable)
        self._update_packets_by_id()

    def _update_packets_by_id(self):
        d = collections.defaultdict(list)
        for pkt in self: d[pkt[0]].append(pkt)
        d.default_factory = None
        self.by_pid = d


class Packet(collections.namedtuple("Packet", ["pid", "length", "data"])):
    
    pass


def A000(executor, stream):
    return executor(stream, L000.PID_PRODUCT_RQST)
        
def A1000(executor, stream):
    return [
        executor(stream, L001.PID_COMMAND_DATA, A010.CMND_TRANSFER_RUNS),
        executor(stream, L001.PID_COMMAND_DATA, A010.CMND_TRANSFER_LAPS),
        executor(stream, L001.PID_COMMAND_DATA, A010.CMND_TRANSFER_TRK),
    ]

class DataType(collections.namedtuple("Unimplemented", ["pid", "length", "data"])):
    
    def __new__(cls, pid, length, data):
        try:
            cls = globals()["D%03d" % pid]
        except KeyError:
            pass
        print cls
        return super(DataType, cls).__new__(cls, pid, length, data)

    def __str__(self):
        return "D%03d:Unimplemented length=%d" % (self.pid, self.length)

    def __repr__(self):
        return str(self)


class D255(DataType):

    def __init__(self, pid, length, data):
        super(D255, self).__init__(pid, length, data)
        self.product_id, self.software_version = struct.unpack("<Hh", data[:4])
        self.description = [str for str in data[4:].split("\x00") if str]

    def __str__(self):
        return ("D255:ProductData: product_id=0x%04x, software_version=%0.2f, product_description=%s"
                % (self.product_id, self.software_version / 100., self.description))


class D248(DataType):
    
    def __init__(self, pid, length, data):
        super(D248, self).__init__(pid, length, data)
        self.description = [str for str in data.split("\x00") if str]
        
    def __str__(self):
        return "D248:ExtProductData: %s" % self.description


class D253(DataType):
    
    def __init__(self, pid, length, data):
        super(D253, self).__init__(pid, length, data)
        self.protocol_array = ["%s%03d" % (proto, ord(msb) << 8 | ord(lsb)) for proto, lsb, msb in chunk(data, 3)]

    def __str__(self):
        return "D253:ProtocolArray: %s" % self.protocol_array


class D012(DataType):

    def __init__(self, pid, length, data):
        super(D012, self).__init__(pid, length, data)
        self.command_id = struct.unpack("<H", data)

    def __str__(self):
        return "D012:XferComplete: command_id=%d" % self.command_id


class D027(DataType):

    def __init__(self, pid, length, data):
        super(D027, self).__init__(pid, length, data)
        self.record_type = struct.unpack("<H", data)

    def __str__(self):
        return "D027:Records: count=%d" % self.record_type
    

# vim: ts=4 sts=4 et
