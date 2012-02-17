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

"""
Implementation of the Garmin Device Interface Specifications.
http://www8.garmin.com/support/commProtocol.html
Classes named like Annn, Dnnn coorelate with the documented
types in specification. Currently this class only implementes
the necessary protocols and datatypes  to dynamically discover
device capaibilties and save runs. The spec was last updated
in 2006, so some datatypes include undocumented/unkown fields.
"""

import logging
import struct
import time
import collections

import antd.ant as ant

_log = logging.getLogger("antd.garmin")

class P000(object):
    """
    Physical protocol, must be implemented by all devices.
    """
    PID_ACK = 6
    PID_NACK = 21

class L000(P000):
    """
    Data link protocl at least PID_PRODUCT_RQST
    is impelmented by all devices.
    """
    PID_PROTOCOL_ARRAY = 253
    PID_PRODUCT_RQST = 254
    PID_PRODUCT_DATA = 255
    PID_EXT_PRODUCT_DATA = 248

    def __init__(self):
        self.data_type_by_pid = {
            L000.PID_PRODUCT_DATA: ProductDataType,
            L000.PID_EXT_PRODUCT_DATA: ExtProductDataType,
            L000.PID_PROTOCOL_ARRAY: ProtocolArrayType,
        }

class L001(L000):
    """
    Link protocol defining how data is requested and
    returned from device. 
    """
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
    # undocumented, assuming this was added
    # due to inefficiency in packet per wpt
    # over ANT
    PID_TRK_DATA_ARRAY = 1510

    def __init__(self):
        self.data_type_by_pid = {
            L001.PID_XFER_CMPLT: CommandIdType,
            L001.PID_RECORDS: RecordsType,
        }

class A010(object):
    """
    Command protocol. Mainly used in comination with
    L001.PID_COMMAND_DATA to download data from device.
    """
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

    def __init__(self):
        self.data_type_by_pid = {}


def dump_packet(file, packet):
    """
    Dump the given packet to file.
    Format is consistant with garmin physical packet format.
    uint16=packet_id, uint16t=data_length, char[]=data
    """
    pid, length, data = packet
    file.write(struct.pack("<HH", pid, length))
    if data: file.write(data.raw)

def dump(file, data):
    """
    Recursively dump the given packets (or packet)
    to given file.
    """
    for packet in data:
        try:
            dump(file, packet)
        except TypeError:
            dump_packet(file, packet)

def pack(pid, data_type=None):
    """
    Pack a garmin request pack, data_type
    if non-None is assumed to be uint16_t.
    packet padded to 8-bytes (FIXME, padding
    is done for ant transport. unportable
    and not even necessary?
    """
    return struct.pack("<HHHxx", pid, 0 if data_type is None else 2, data_type or 0)

def unpack(msg):
    """
    Unpack a garmin device communication packet.
    uint16_t=pid, uint16_t=length, data[]
    """
    pid, length = struct.unpack("<HH", msg[:4])
    data = msg[4:4 + length]
    return pid, length, data

def tokenize(msg):
    """
    A generator which returning unpacked
    packets from the given string of concatinated
    packet strings.
    """
    while True:
        pid, length, data = unpack(msg)
        if pid or length:
            yield pid, length, msg[4:length + 4] 
            msg = msg[length + 4:]
            if len(msg) < 4: break
        else:
            break

def chunk(l, n):
    """
    A generator returning n-sized lists
    of l's elements.
    """
    for i in xrange(0, len(l), n):
        yield l[i:i+n]

def get_proto_cls(protocol_array, values):
    """
    Given a garmin protocol_array, return
    the first value in values which is implemented
    by the device.
    """
    for val in values:
        if val.__name__ in protocol_array:
            return val

def data_types_by_protocol(protocol_array):
    """
    Return a dict mapping each protocol Annn
    to the data types returned by the device
    descrived by protocol array.
    """
    result = {}
    for proto in protocol_array:
        if "A" in proto:
            data_types = []
            result[proto] = data_types
        elif "D" in proto:
            data_types.append(proto)
    return result

def abbrev(str, max_len):
    """
    Return a string  of up to max length.
    adding elippis if string greater than max len.
    """
    if len(str) > max_len: return str[:max_len] + "..."
    else: return str

def extract_wpts(protocols, get_trks_pkts, index):
    """
    Given a collection of track points packets,
    return those which are members of given track index.
    Where PID_TRK_DATA_ARRAY is encountered, data is expanded
    such that result is equvalent to cas where each was its
    on packet of PID_TRK_DATA
    """
    i = iter(get_trks_pkts)
    # position iter at first wpt record of given index
    for pid, length, data in i:
        if pid == protocols.link_proto.PID_TRK_HDR and data.index == index:
            break
    # extract wpts
    for pkt in i:
        if pkt.pid == protocols.link_proto.PID_TRK_HDR:
            break
        elif pkt.pid == protocols.link_proto.PID_TRK_DATA:
            yield data
        elif pkt.pid == protocols.link_proto.PID_TRK_DATA_ARRAY:
            for wpt in pkt.data.wpts: yield wpt

def extract_runs(protocols, get_runs_pkts):
    """
    Given garmin packets which are result of A1000 (get_runs)
    Return an object tree runs->laps->points for easier processing.
    """
    runs, laps, trks = get_runs_pkts
    runs = [r.data for r in runs.by_pid[protocols.link_proto.PID_RUN]]
    laps = [l.data for l in laps.by_pid[protocols.link_proto.PID_LAP]]
    _log.debug("extract_runs: found %d run(s)", len(runs))
    for run_num, run in enumerate(runs):
        run.laps = [l for l in laps if run.first_lap_index <= l.index <= run.last_lap_index]
        run.time.time = run.laps[0].start_time.time
        run.wpts = list(extract_wpts(protocols, trks, run.track_index))
        _log.debug("extract_runs: run %d has: %d lap(s), %d wpt(s)", run_num + 1, len(run.laps), len(run.wpts))
        for lap in run.laps: lap.wpts = []
        lap_num = 0
        for wpt in run.wpts:
            try:
                while wpt.time.time >= run.laps[lap_num + 1].start_time.time:
                    _log.debug("extract_runs: run %d lap %d has: %d wpt(s)",
                            run_num + 1, lap_num + 1, len(run.laps[lap_num].wpts))
                    lap_num += 1
            except IndexError:
                pass
            run.laps[lap_num].wpts.append(wpt)
        all_wpt_in_laps = sum(len(lap.wpts) for lap in run.laps)
        if len(run.wpts) != all_wpt_in_laps:
            _log.warning("extract_runs: run %d waypoint mismatch: total(%d) != wpt_in_laps(%d)",
                    run_num + 1, len(run.wpts), all_wpt_in_laps)
    return runs


class Device(object):
    """
    Class represents a garmin gps device.
    Methods of this class will delegate to
    the specific protocols impelemnted by this
    device. They may raise DeviceNotSupportedError
    if the device does not implement a specific
    operation.
    """
    
    def __init__(self, stream):
        self.stream = stream
        self.init_device_api()

    def get_product_data(self):
        """
        Get product capabilities.
        """
        return self.execute(A000())[0]

    def get_runs(self):
        """
        Get new runs from device.
        """
        if self.run_proto:
            return self.execute(self.run_proto)
        else:
            raise DeviceNotSupportedError("Device does not support get_runs.")

    def init_device_api(self):
        """
        Initialize the protocols used by this
        instance based on the protocol capabilities
        array which is return from A000.
        """
        product_data = self.get_product_data()
        try:
            self.device_id = product_data.by_pid[L000.PID_PRODUCT_DATA][0].data
            self.protocol_array = product_data.by_pid[L000.PID_PROTOCOL_ARRAY][0].data.protocol_array
            _log.debug("init_device_api: product_id=%d, software_version=%0.2f, description=%s",
                    self.device_id.product_id, self.device_id.software_version/100., self.device_id.description)
            _log.debug("init_device_api: protocol_array=%s", self.protocol_array)
        except (IndexError, TypeError):
            raise DeviceNotSupportedError("Product data not returned by device.")
        self.data_types_by_protocol = data_types_by_protocol(self.protocol_array)
        # the tuples in this section define an ordered collection
        # of protocols which are candidates to provide each specific
        # function. Each proto will be device based on the first one
        # whihc exists in this devices capabiltities.
        # This section needs to be updated whenever a new protocol 
        # needs to be supported.
        self.link_proto = self._find_core_protocol("link", (L000, L001))
        self.cmd_proto = self._find_core_protocol("command", (A010,))
        self.trk_proto = self._find_app_protocol("get_trks", (A301, A302))
        self.lap_proto = self._find_app_protocol("get_laps", (A906,))
        self.run_proto = self._find_app_protocol("get_runs", (A1000,))

    def _find_core_protocol(self, name, candidates):
        """
        Return the first procotol in candidates
        which is supported by this device.
        """
        proto = get_proto_cls(self.protocol_array, candidates)
        if proto:
            _log.debug("Using %s protocol %s.", name, proto.__name__)
        else:
            raise DeviceNotSupportedError("Device does not implement a known link protocol. capabilities=%s" 
                    % self.protocol_array)
        return proto()

    def _find_app_protocol(self, function_name, candidates):
        """
        Return the first protocol in candidates whihc
        is supported by this device. additionally, check
        that the datatypes which are returned by the give
        protocol are implented by this python module.
        If not a warning is logged. (but no excetpion is raised._
        This allows raw data dump to succeed, but trx generation to fail.
        """
        cls = get_proto_cls(self.protocol_array, candidates)
        data_types = self.data_types_by_protocol.get(cls.__name__, [])
        data_type_cls = [globals().get(nm, DataType) for nm in data_types]
        if not cls:
            _log.warning("Download may FAIL. Protocol unimplemented. %s:%s", function_name, candidates)
        else:
            _log.debug("Using %s%s for: %s", cls.__name__, data_types, function_name)
            if DataType in data_type_cls:
                _log.warning("Download may FAIL. DataType unimplemented. %s:%s%s", function_name, cls.__name__, data_types)
            try:
                return cls(self, *data_type_cls)
            except Exception:
                _log.warning("Download may Fail. Failed to ceate protocol %s.", function_name, exc_info=True)

    def execute(self, protocol):
        """
        Execute the give garmin Applection protcol.
        e.g. one of the Annn classes.
        """
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
    """
    A mock device which can be used
    when instantiating a Device.
    Rather than accessing hardware,
    commands are replayed though given
    string (which can be read from file.
    This class is dumb, so caller has
    to ensure pkts in the import string
    or file are properly ordered.
    """

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
    """
    A protocol defines the required comands
    which need to be sent to hardware to perform
    a specific function.
    """

    def __init__(self, protocols):
        self.link_proto = protocols.link_proto
        self.cmd_proto = protocols.cmd_proto
        self.data_type_by_pid = dict(
            protocols.link_proto.data_type_by_pid.items() +
            protocols.cmd_proto.data_type_by_pid.items()
        )

    def execute(self):
        """
        A generator or array which contains either a tuple
        representing a command which should be executed
        or a protocol (who's execute shoudl be deletaged to.
        """
        return []

    def decode_packet(self, pid, length, data):
        """
        Decode the given packet's data property.
        """
        if length:
            data_cls = self.data_type_by_pid.get(pid, DataType)
            return data_cls(data)

    def decode_list(self, pkts):
        return PacketList(pkts)

    def decode_result(self, list):
        return list

class DownloadProtocol(Protocol):
    """
    Protocol with download progess logging.
    Can be extended/ehnanced for GUI use.
    """

    pid_data = []

    def decode_packet(self, pid, length, data):
        data = super(DownloadProtocol, self).decode_packet(pid, length, data)
        try:
            if pid == self.link_proto.PID_RECORDS:
                self.on_start(pid, data)
            elif pid in self.pid_data:
                self.on_data(pid, data)
            elif pid == self.link_proto.PID_XFER_CMPLT:
                self.on_finish(pid, data)
        except Exception:
            # notification may fail if data packet could not be enriched by a known data type?
            # dont' allow this to stop the download, still want to write raw packets to file.
            _log.warning("Caught exception sending notification of download status, ignoring error", exc_info=True)
        finally:
            return data
            

    def on_start(self, pid, data):
        _log.info("%s: Starting download. %d record(s)", self.__class__.__name__, data.count)
        self.expected = data.count
        self.count = 0
        self.last_log = time.time()

    def on_data(self, pid, data):
        self.count += 1
        if self.last_log + 1 < time.time():
            _log.info("%s: Download in progress. %d/%d", self.__class__.__name__, self.count, self.expected)
            self.last_log = time.time()

    def on_finish(self, pid, data):
        _log.info("%s: Finished download. %d/%d", self.__class__.__name__, self.count, self.expected)
        if self.count != self.expected:
            _log.warning("%s: Record count mismatch, expected(%d) != actual(%d)", 
                    self.__class__.__name__, self.expected, self.count)
    

class A000(Protocol):
    """
    Device capabilities.
    """

    def __init__(self):
        self.data_type_by_pid = L000().data_type_by_pid

    def execute(self):
        _log.debug("A000: executing product request")
        yield (L000.PID_PRODUCT_RQST, None)


class A1000(DownloadProtocol):
    """
    Get runs.
    """

    def __init__(self, protocols, run_type):
        super(A1000, self).__init__(protocols)
        if not protocols.lap_proto or not protocols.trk_proto:
            raise DeviceNotSupportedError("A1000 required device to supoprt lap and track protocols.")
        self.lap_proto = protocols.lap_proto
        self.trk_proto = protocols.trk_proto
        self.data_type_by_pid.update({
            self.link_proto.PID_RUN: run_type,
        })
        self.pid_data = [self.link_proto.PID_RUN]
        
    def execute(self):
        _log.debug("A1000: executing transfer runs")
        yield (self.link_proto.PID_COMMAND_DATA, self.cmd_proto.CMND_TRANSFER_RUNS)
        yield self.lap_proto
        yield self.trk_proto


class A301(DownloadProtocol):
    """
    Get tracks
    """

    def __init__(self, protocols, trk_hdr_type, trk_type):
        super(A301, self).__init__(protocols)
        self.data_type_by_pid.update({
            self.link_proto.PID_TRK_HDR: trk_hdr_type,
            self.link_proto.PID_TRK_DATA: trk_type,
            self.link_proto.PID_TRK_DATA_ARRAY: trk_type,
        })
        self.pid_data = [
            self.link_proto.PID_TRK_HDR,
            self.link_proto.PID_TRK_DATA,
            self.link_proto.PID_TRK_DATA_ARRAY,
        ]

    def execute(self):
        _log.debug("A301: executing transfer tracks")
        yield (self.link_proto.PID_COMMAND_DATA, self.cmd_proto.CMND_TRANSFER_TRK)

    def on_data(self, pid, data):
        """
        PID_TRK_DATA_ARRAY return multiple data objects per
        packet, override default products implementation to override.
        """
        if pid == self.link_proto.PID_TRK_DATA_ARRAY:
            self.count += data.num_valid_wpt - 1
        super(A301, self).on_data(pid, data)


class A302(A301):
    """
    Same as 301
    """


class A906(DownloadProtocol):
    """
    Get laps
    """

    def __init__(self, protocols, lap_type):
        super(A906, self).__init__(protocols)
        self.data_type_by_pid.update({
            self.link_proto.PID_LAP: lap_type
        })
        self.pid_data = [self.link_proto.PID_LAP]

    def execute(self):
        _log.debug("A906: executing transfer laps")
        yield (self.link_proto.PID_COMMAND_DATA, self.cmd_proto.CMND_TRANSFER_LAPS)


class PacketList(list):

    Packet = collections.namedtuple("Packet", ["pid", "length", "data"])

    def __init__(self, iterable):
        super(PacketList, self).__init__(self.Packet(*i) for i in iterable)
        self._update_packets_by_id()

    def _update_packets_by_id(self):
        d = collections.defaultdict(list)
        for pkt in self: d[pkt[0]].append(pkt)
        self.by_pid = d


class DataType(object):
    """
    DataType is base implementation for parser which
    interpruts the data payload of a garmin packet.
    Default implentation save message .raw property
    but provides no addition properties.
    """

    def __init__(self, raw_str):
        self.raw = raw_str
        self.unparsed = self.raw
        self.str_args = []

    def _unpack(self, format, arg_names):
        """
        Use the givem format to extract the give
        proeprty names from this instance unparsed text.
        """
        sz = struct.calcsize(format)
        data = self.unparsed[:sz]
        self.unparsed = self.unparsed[sz:]
        args = struct.unpack(format, data)
        assert len(args) == len(arg_names)
        for name, arg in zip(arg_names, args):
            setattr(self, name, arg)
        self.str_args.extend(arg_names)
        
    def _parse(self, type, arg_name=None):
        """
        Invoke a composite data type to parse
        from start of this instance's unparsed text.
        If arg_name is provided, reulst will be
        assigned as attribute of this instance.
        """
        data = type(self.unparsed)
        if arg_name:
            setattr(self, arg_name, data)
            self.str_args.append(arg_name)
        self.unparsed = data.unparsed
        data.unparsed = ""
        return data

    def __str__(self):
        parsed_args = [(k, getattr(self, k)) for k in self.str_args]
        if not self.unparsed:
            return "%s%s" % (self.__class__.__name__, parsed_args)
        else:
            return "%s%s, unparsed=%s" % (self.__class__.__name__, parsed_args,
                                          abbrev(self.unparsed.encode("hex"), 32))
        
    def __repr__(self):
        return self.__str__()


class TimeType(DataType):
    
    EPOCH = 631065600 # Dec 31, 1989 @ 12:00am UTC  

    def __init__(self, data):
       super(TimeType, self).__init__(data)
       self._unpack("<I", ["time"])

    @property
    def gmtime(self):
        return time.gmtime(self.EPOCH + self.time)

class PositionType(DataType):
    
    INVALID_SEMI_CIRCLE = 2**31 - 1

    def __init__(self, data):
        super(PositionType, self).__init__(data)
        self._unpack("<ii", ["lat", "lon"])
        self.valid = self.lat != self.INVALID_SEMI_CIRCLE and self.lon != self.INVALID_SEMI_CIRCLE
        if self.valid:
            self.deglat = self.lat * (180. / 2**31)
            self.deglon = self.lon * (180. / 2**31)
        else:
            self.deglat, self.deflon, lat, lon = [None] * 4


class CommandIdType(DataType):
    
    def __init__(self, data):
        super(CommandIdType, self).__init__(data)
        self._unpack("<H", ["command_id"])


class RecordsType(DataType):

    def __init__(self, data):
        super(RecordsType, self).__init__(data)
        self._unpack("<H", ["count"])


class ProductDataType(DataType):

    def __init__(self, data):
        super(ProductDataType, self).__init__(data)
        self._unpack("<Hh", ["product_id", "software_version"])
        self.description = [str for str in self.unparsed.split("\x00") if str]
        self.str_args.append("description")


class ExtProductDataType(DataType):
    
    def __init__(self, data):
        super(ExtProductDataType, self).__init__(data)
        self.description = [str for str in data.split("\x00") if str]
        self.str_args.append("description")


class ProtocolArrayType(DataType):
    
    def __init__(self, data):
        super(ProtocolArrayType, self).__init__(data)
        self.protocol_array = ["%s%03d" % (proto, ord(msb) << 8 | ord(lsb)) for proto, lsb, msb in chunk(data, 3)]
        self.str_args.append("protocol_array")


class WorkoutStepType(DataType):

    def __init__(self, data):
        super(WorkoutStepType, self).__init__(data)
        self._unpack("<16sffHBBBB2x", [
            "custom_name",
            "target_custom_zone_low",
            "target_cusomt_zone_hit",
            "duration_value",
            "intensity",
            "duration_type",
            "target_type",
            "target_value",
        ])
        self.custom_name = self.custom_name[:self.custom_name.index("\x00")]


class D1008(DataType):
    """
    Workout
    """
    
    def __init__(self, data):
        super(D1008, self).__init__(data)
        self._unpack("<I", ["num_valid_steps"])
        self.steps = [None] * self.num_valid_steps
        for step_num in xrange(0, self.num_valid_steps):
            self.steps[step_num] = self._parse(WorkoutStepType)
        self._unpack("<16sb", ["name", "sport_type"])
        self.name = self.name[:self.name.index("\x00")]


class D1009(DataType):
    """
    Run
    """

    def __init__(self, data):
        super(D1009, self).__init__(data)
        self._unpack("<HHHBBBx2x", [
            "track_index",
            "first_lap_index",
            "last_lap_index",
            "sport_type",
            "program_type",
            "multisport",
        ])
        self._parse(TimeType, "time")
        self._unpack("<f", ["distance"])
        self.workout = D1008(self.unparsed)
        self.unparsed = self.workout.unparsed
        self.workout.unparsed = ""
        self.str_args.append("workout")


class D1011(DataType):
    """
    Lap
    """

    def __init__(self, data):
        super(D1011, self).__init__(data)
        self._unpack("<H2x", ["index"])
        self._parse(TimeType, "start_time")
        self._unpack("<Iff", [
            "total_time",
            "total_dist",
            "max_speed",
        ])
        self._parse(PositionType, "begin")
        self._parse(PositionType, "end")
        self._unpack("HBBBBB", [
            "calories",
            "avg_heart_rate",
            "max_heart_rate",
            "intensity",
            "avg_cadence",
            "trigger_method",
        ])
        if self.avg_heart_rate == 0: self.avg_heart_rate = None
        if self.max_heart_rate == 0: self.max_heart_rate = None
        if self.avg_cadence == 0xFF: self.avg_cadence = None


class D1015(D1011):
    """
    Lap + extra mystery bytes
    """

    def __init__(self, data):
        super(D1015, self).__init__(data)
        self._unpack("BBBBB", [
            "undocumented_0",
            "undocumented_1",
            "undocumented_2",
            "undocumented_3",
            "undocumented_4",
        ])


class D311(DataType):
    """
    wpt header
    """
    
    def __init__(self, data):
        super(D311, self).__init__(data)
        self._unpack("<H", ["index"])


class D304(DataType):
    """
    way point
    """
    
    INVALID_FLOAT = struct.unpack("<f", "\x51\x59\x04\x69")[0]

    def __init__(self, data):
        super(D304, self).__init__(data)
        self._parse(PositionType, "posn")
        self._parse(TimeType, "time")
        self._unpack("<ffBBB", [
            "alt",
            "distance",
            "heart_rate",
            "cadence",
            "sensor",
        ])
        if self.alt == self.INVALID_FLOAT: self.alt = None
        if self.distance == self.INVALID_FLOAT: self.distance = None
        if self.cadence == 0xFF: self.cadence = None
        if self.heart_rate == 0: self.heart_rate = None


class D1018(DataType):
    """
    An array of waypoints
    undocumented.
    """
    
    def __init__(self, data):
        super(D1018, self).__init__(data)
        self._unpack("<I", ["num_valid_wpt"])
        self.wpts = [None] * self.num_valid_wpt
        self.str_args.append("wpts")
        for n in xrange(0, self.num_valid_wpt):
            self.wpts[n] = self._parse(D304)
            # word alignment
            self.unparsed = self.unparsed[1:]
        

class DeviceNotSupportedError(Exception):
    """
    Raised device capabilites lack capabilites
    to complete request.
    """


# vim: ts=4 sts=4 et
