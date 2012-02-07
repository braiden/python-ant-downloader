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

def data_types_by_protocol(protocol_array):
    result = {}
    for proto in protocol_array:
        if "A" in proto:
            data_types = []
            result[proto] = data_types
        elif "D" in proto:
            data_types.append(proto)
    return result


class Device(object):

    def __init__(self, stream):
        self.stream = stream

    def get_product_data(self):
        """
        Get product capabilities.
        """
        return self.execute(A000())

    def get_runs(self):
        # FIXME the protocols used for device
        # should be discovered based on product data
        trk = A302(L001, A010)
        lap = A907(L001, A010)
        run = A1000(L001, A010, lap, trk)
        return self.execute(run)

#    def init_device_api(self):
#        product_data = self.get_product_data()
#        try:
#            device_id = product_data.by_pid[L000.PID_PRODUCT_DATA][0]
#            protocol_array = product_data.by_pid[L000.PID_PROTOCOL_ARRAY][0]
#        except (IndexError, TypeError):
#            raise DeviceNotSupportedError("Product data not returned by device.")
#        _log.debug("init_device_api: product_id=%d, software_version=%d, description=%s",
#                device_id.data.product_id, device_id.data.software_version, device_id.data.description)
#        self.data_types = data_types_by_protocol(protocol_array.data.protocol_array)
#        if "A010" in protocol_array.data.protocol_array:
#            self.api = A010
#            try:
#                self.run_type = self.data_types["A1000"][0]
#                self.lap_type = self.data_types["A906"][0]
#                self.wpt_hdr_type = self.data_types["A302"][0]
#                self.wpt_type = self.data_types["A302"][1]
#            except KeyError:
#                raise DeviceNotSupportedError("Device does not implement A1000 or required sub-protocol. capabilities=%s" % protocol_array.data.protocol_array)
#            _log.debug("A1000 datatypes. run=%s, lap=%s, wpt_hdr=%s, wpt=%s", self.run_type, self.lap_type, self.wpt_hdr_type, self.wpt_type)
#        else:
#            raise DeviceNotSupportedError("Device does not implement a known application protocol. capabilities=%s" % protocol_array.data.protocol_array)
#        if "L001" in protocol_array.data.protocol_array:
#            self.link = L001
#            self.data_types.update({
#                L001.PID_RECORDS: D027,
#                L001.PID_XFER_CMPLT: D012,
#            })
#        else:
#            raise DeviceNotSupportedError("Device does not implement a known link protocol. capabilities=%s" % protocol_array.data.protocol_array)
#
#
#    def get_runs(self):
#        """
#        Download runs. A1000
#        """
#        runs = self.execute(self.link.PID_COMMAND_DATA, self.api.CMND_TRANSFER_RUNS)
#        laps = self.execute(self.link.PID_COMMAND_DATA, self.api.CMND_TRANSFER_LAPS)
#        waypoints = self.execute(self.link.PID_COMMAND_DATA, self.api.CMND_TRANSFER_TRK)
#        return (runs, laps, waypoints)

    def execute(self, protocol):
        result = []
        for next in protocol.execute():
            if hasattr(next, "execute"):
                result.extend(self.execute(next))
            else:
                pid, data = next
                in_packets = []
                self.stream.write(pack(pid, data))
                while True:
                    pkt = self.stream.read()
                    if not pkt: break
                    for pid, length, data in tokenize(pkt):
                        in_packets.append((pid, length, protocol.decode_packet(pid, length, data)))
                        self.stream.write(pack(P000.PID_ACK, pid))
                in_packets.append((0, 0, None))
                result.append(protocol.decode_list(in_packets))

        return protocol.decode_result(result)


class MockHost(object):

    def __init__(self, data):
        self.reader = self._read(data)

    def write(self, *args, **kwds):
        pass

    def read(self):
        try:
            return self.reader.next()
        except StopIteration:
            return ""

    def _read(self, data):
        while data:
            (length,) = struct.unpack("<H", data[2:4])
            if length: pkt = data[0:length + 4]
            else: pkt = ""
            data = data[length + 4:]
            yield pkt


class Protocol(object):

    def __init__(self, link_proto, cmd_proto):
        self.data_type_by_pid = {}
        self.link_proto = link_proto
        self.cmd_proto = cmd_proto

    def execute(self):
        return []

    def decode_packet(self, pid, length, data):
        if length:
            data_cls = self.data_type_by_pid.get(pid, DataType)
            return data_cls(pid, data)

    def decode_list(self, pkts):
        return PacketList(pkts)

    def decode_result(self, lists):
        return lists


class A000(Protocol):

    def __init__(self):
        self.data_type_by_pid = {
            L000.PID_PRODUCT_DATA: D255,
            L000.PID_EXT_PRODUCT_DATA: D248,
            L000.PID_PROTOCOL_ARRAY: D253,
        }

    def execute(self):
        yield (L000.PID_PRODUCT_RQST, None)


class A1000(Protocol):

    def __init__(self, link_proto, cmd_proto, track_proto, wpt_proto):
        super(A1000, self).__init__(link_proto, cmd_proto)
        self.track_proto = track_proto
        self.wpt_proto = wpt_proto
        
    def execute(self):
        yield (self.link_proto.PID_COMMAND_DATA, self.cmd_proto.CMND_TRANSFER_RUNS)
        yield self.track_proto
        yield self.wpt_proto


class A302(Protocol):

    def __init__(self, link_proto, cmd_proto):
        super(A302, self).__init__(link_proto, cmd_proto)

    def execute(self):
        yield (self.link_proto.PID_COMMAND_DATA, self.cmd_proto.CMND_TRANSFER_TRK)


class A907(Protocol):

    def __init__(self, link_proto, cmd_proto):
        super(A907, self).__init__(link_proto, cmd_proto)

    def execute(self):
        yield (self.link_proto.PID_COMMAND_DATA, self.cmd_proto.CMND_TRANSFER_LAPS)


class PacketList(list):

    Packet = collections.namedtuple("Packet", ["pid", "length", "data"])

    def __init__(self, iterable):
        super(PacketList, self).__init__(self.Packet(*i) for i in iterable)
        self._update_packets_by_id()

    def _update_packets_by_id(self):
        d = collections.defaultdict(list)
        for pkt in self: d[pkt[0]].append(pkt)
        d.default_factory = None
        self.by_pid = d


class DataType(object):

    def __init__(self, type_id, raw_str):
        self.type_id = type_id
        self.raw = raw_str
        self.unparsed = self.raw
        self.str_args = []

    def _unpack(self, format, arg_names):
        sz = struct.calcsize(format)
        data = self.unparsed[:sz]
        self.unparsed = self.unparsed[sz:]
        args = struct.unpack(format, data)
        assert len(args) == len(arg_names)
        for name, arg in zip(arg_names, args):
            setattr(self, name, arg)
        self.str_args.extend(arg_names)
        
    def __str__(self):
        parsed_args = dict((k, getattr(self, k)) for k in self.str_args)
        return "D%03d%s" % (self.type_id, parsed_args)
        
    def __repr__(self):
        return self.__str__()


class D012(DataType):
    
    def __init__(self, pid, data):
        super(D012, self).__init__(pid, data)
        self._unpack("<H", ["command_id"])

class D027(DataType):

    def __init__(self, pid, data):
        super(D027, self).__init__(pid, data)
        self._unpack("<H", ["count"])


class D255(DataType):

    def __init__(self, pid, data):
        super(D255, self).__init__(pid, data)
        self._unpack("<Hh", ["product_id", "software_version"])
        self.description = [str for str in self.unparsed.split("\x00") if str]
        self.str_args.append("description")


class D248(DataType):
    
    def __init__(self, pid, data):
        super(D248, self).__init__(pid, data)
        self.description = [str for str in data.split("\x00") if str]
        self.str_args.append("description")


class D253(DataType):
    
    def __init__(self, pid, data):
        super(D253, self).__init__(pid, data)
        self.protocol_array = ["%s%03d" % (proto, ord(msb) << 8 | ord(lsb)) for proto, lsb, msb in chunk(data, 3)]
        self.str_args.append("protocol_array")


class DeviceNotSupportedError(Exception): pass


# vim: ts=4 sts=4 et
