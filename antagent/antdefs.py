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


import collections
import struct

SYNC = 0xA4

DIR_IN = "IN"
DIR_OUT = "OUT"

TYPE_CONFIG = "CONFIG"
TYPE_NOTIFICATION = "NOTIFICATION"
TYPE_CONTROL = "CONTROL"
TYPE_DATA = "DATA"
TYPE_CHANNEL_EVENT = "CHANNEL_EVENT"
TYPE_REPLY = "REPLY"

RESPONSE_NO_ERROR = 0
CHANNEL_IN_WRONG_STATE = 21
CHANNEL_NOT_OPENED = 22
CHANNEL_ID_NOT_SET = 24
CLOSE_ALL_CHANNELS = 25
TRANSFER_IN_PROGRESS = 31
TRANSFER_SEQUENCE_NUMBER_ERROR = 32
TANNSFER_IN_ERROR = 33
MESSAGE_SIZE_EXCEEDS_LIMIT = 39
INVALID_MESSAGE = 40
INVALID_NETWORK_NUMBER = 41
INVALID_LIST_ID = 48
INVALID_SCAN_TX_CHANNEL = 49
INVALID_PARAMETER_PROVIDED = 51
NVM_FULL_ERROR = 64
NVM_WRITE_ERROR = 65
USB_STRING_WRITE_FAIL = 112
MESG_SERIAL_ERROR_ID = 174

EVENT_RX_SEARCH_TIMEOUT = 1
EVENT_RX_FAIL = 2
EVENT_TX = 3
EVENT_TRANSFER_RX_FAILED = 4
EVENT_TRANSFER_TX_COMPLETED = 5
EVENT_TRANSFER_TX_FAILED = 6
EVENT_CHANNEL_CLOSED = 7
EVENT_RX_FAIL_TO_SEARCH = 8
EVENT_CHANNEL_COLLISION = 9
EVENT_TRANSFER_TX_START = 10
EVENT_SERIAL_QUEUE_OVERFLOW = 52
EVENT_QUEUE_OVERFLOW = 53

class AntMessage(object):

    def __init__(self, msg_dir, msg_type, msg_name, msg_id, msg_format, msg_args):
        self.msg_dir = msg_dir
        self.msg_type = msg_type
        self.msg_name = msg_name
        self.msg_id = msg_id
        self.msg_format = msg_format
        self.msg_args = msg_args
        if self.msg_format is not None:
            self.msg_struct = struct.Struct("<" + self.msg_format)
        if self.msg_args is not None:
            self.msg_tuple = collections.namedtuple(self.msg_name, self.msg_args)
    
    def __int__(self):
        return self.msg_id


UNASSIGN_CHANNEL = AntMessage(DIR_OUT, TYPE_CONFIG, "UNASSIGN_CHANNEL", 0x41, "B", ["channel_number"])
ASSIGN_CHANNEL = AntMessage(DIR_OUT, TYPE_CONFIG, "ASSIGN_CHANNEL", 0x42, "BBB", ["channel_number", "channel_type", "network_number"])
SET_CHANNEL_ID = AntMessage(DIR_OUT, TYPE_CONFIG, "SET_CHANNEL_ID", 0x51, "BHBB", ["channel_number", "device_number", "device_type_id", "trans_type"])
SET_CHANNEL_PERIOD = AntMessage(DIR_OUT, TYPE_CONFIG, "SET_CHANNEL_PERIOD", 0x43, "BH", ["channel_number", "messaging_period"]) 
SET_CHANNEL_SEARCH_TIMEOUT = AntMessage(DIR_OUT, TYPE_CONFIG, "SET_CHANNEL_SEARCH_TIMEOUT", 0x44, "BB", ["channel_number", "search_timeout"])
SET_CHANNEL_RF_FREQ = AntMessage(DIR_OUT, TYPE_CONFIG, "SET_CHANNEL_RF_FREQ", 0x45, "BB", ["channel_number", "search_timeout"])
SET_NEWORK_KEY = AntMessage(DIR_OUT, TYPE_CONFIG, "SET_NETWORK_KEY", 0x46, "BQ", ["network_number", "network_key"])
RESET_SYSTEM = AntMessage(DIR_OUT, TYPE_CONTROL, "RESET_SYSTEM", 0x4a, "x", [])
OPEN_CHANNEL = AntMessage(DIR_OUT, TYPE_CONTROL, "OPEN_CHANNEL", 0x4b, "B", ["channel_number"])
CLOSE_CHANNEL = AntMessage(DIR_OUT, TYPE_CONTROL, "CLOSE_CHANNEL", 0x4c, "B", ["channel_number"])
REQUEST_MESSAGE = AntMessage(DIR_OUT, TYPE_CONTROL, "REQUEST_MESSAGE", 0x4d, "BB", ["channel_number"])
SET_SEARCH_WAVEFORM = AntMessage(DIR_OUT, TYPE_CONTROL, "SET_SEARCH_WAVEFORM", 0x49, "BH", ["channel_number", "waveform"])
SEND_BROADCAST_DATA = AntMessage(DIR_OUT, TYPE_DATA, "SEND_BROADCAST_DATA", 0x4e, "B8s", ["channel_number", "data"])
SEND_ACKNOWLEDGED_DATA = AntMessage(DIR_OUT, TYPE_DATA, "SEND_ACKNOWLEDGED_DATA", 0x4f, "B8s", ["channel_number", "data"])
SEND_BURST_TRANSFER_PACKET = AntMessage(DIR_OUT, TYPE_DATA, "SEND_BURST_TRANSFER_PACKET", 0x50, "B8s", ["channel_number", "data"])
STARTUP_MESSAGE = AntMessage(DIR_IN, TYPE_NOTIFICATION, "STARTUP_MESSAGE", 0x6f, "B", ["startup_message"])
SERIAL_ERROR = AntMessage(DIR_IN, TYPE_NOTIFICATION, "SERIAL_ERROR", 0xae, None, None)
RECV_BROADCAST_DATA = AntMessage(DIR_IN, TYPE_DATA, "RECV_BROADCAST_DATA", 0x4e, "B8s", ["channel_number", "data"])
RECV_ACKNOWLEDGED_DATA = AntMessage(DIR_IN, TYPE_DATA, "RECV_ACKNOWLEDGED_DATA", 0x4f, "B8s", ["channel_number", "data"])
RECV_BURST_TRANSFER_PACKET = AntMessage(DIR_IN, TYPE_DATA, "RECV_BURST_TRANSFER_PACKET", 0x50, "B8s", ["channel_number", "data"])
CHANNEL_EVENT = AntMessage(DIR_IN, TYPE_CHANNEL_EVENT, "CHANNEL_EVENT", 0x40, "BBB", ["channel_number", "msg_id", "msg_code"])
CHANNEL_STATUS = AntMessage(DIR_IN, TYPE_REPLY, "CHANNEL_STATUS", 0x52, "BB", ["channel_number", "channel_status"])
CHANNEL_ID = AntMessage(DIR_IN, TYPE_REPLY, "CHANNEL_ID", 0x51, "BHBB", ["channel_number", "device_number", "device_type_id", "man_id"])
VERSION = AntMessage(DIR_IN, TYPE_REPLY, "VERSION", 0x3e, "11s", ["ant_version"])
CAPABILITIES = AntMessage(DIR_IN, TYPE_REPLY, "CAPABILITIES", 0x54, "BBBBBx", ["max_channels", "max_networks", "standard_opts", "advanced_opts1", "advanced_opts2"])

ALL_MESSAGES = [
    UNASSIGN_CHANNEL,
    ASSIGN_CHANNEL,
    SET_CHANNEL_ID,
    SET_CHANNEL_PERIOD,
    SET_CHANNEL_SEARCH_TIMEOUT,
    SET_CHANNEL_RF_FREQ,
    SET_NEWORK_KEY,
    RESET_SYSTEM,
    OPEN_CHANNEL,
    CLOSE_CHANNEL,
    REQUEST_MESSAGE,
    SET_SEARCH_WAVEFORM,
    SEND_BROADCAST_DATA,
    SEND_ACKNOWLEDGED_DATA,
    SEND_BURST_TRANSFER_PACKET,
    STARTUP_MESSAGE,
    SERIAL_ERROR,
    RECV_BROADCAST_DATA,
    RECV_ACKNOWLEDGED_DATA,
    RECV_BURST_TRANSFER_PACKET,
    CHANNEL_EVENT,
    CHANNEL_STATUS,
    CHANNEL_ID,
    VERSION,
    CAPABILITIES,
]

# vim: ts=4 sts=4 et
