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
import collections
import Queue

from antagent.antdefs import *

_LOG = logging.getLogger("antagent.ant")
DEFAULT_TIMEOUT = 250

def generate_checksum(msg):
    return reduce(lambda x, y: x ^ y, msg)

def validate_checksum(msg):
    return generate_checksum(msg) == 0

def tokenize_message(msg):
    while msg:
        assert ord(msg[0]) & 0xFE == SYNC
        length = ord(msg[1])
        yield msg[:4 + length]
        msg = msg[4 + length:]


class AntCommand(object):

    def __init__(self, msg_type, *args, **kwds):
        self.msg_type = msg_type
        try:
            self.msg_args = msg_type.msg_tuple(*args, **kwds)
        except AttributeError:
            self.msg_args = args

    def __str__(self):
        return str(self.msg_args)


class AntCore(object):
    
    def __init__(self, hardware, messages=ALL_MESSAGES):
        self.hardware = hardware
        self.input_msg_by_id = dict((m.msg_id, m) for m in messages if m.msg_dir == DIR_IN)

    def pack(self, command):
        if command.msg_type.msg_id == DIR_IN:
            _LOG.warning("Request to pack input message %s.", command)
        try:
            struct = command.msg_type.msg_struct
        except AttributeError:
            _LOG.warning("Attempt to pack unsupported command %s.", command)
            return []
        else:
            msg = [SYNC, struct.size, command.msg_type.msg_id]
            msg.extend(array.array("B", struct.pack(*command.msg_args)))
            msg.append(generate_checksum(msg))
            return msg
    
    def unpack(self, msg):
        if not validate_checksum(msg):
            raise IOError("Invalid Checksum", msg)
        sync, length, msg_id = msg[:3]
        try:
            msg_type = self.input_msg_by_id[msg_id]
            struct = msg_type.msg_struct
        except (KeyError, AttributeError):
            _LOG.warning("Attempt to unpack unkown message (0x%02x) %s.", msg_id, msg)
            return AntCommand(msg_id)
        else:
            msg_args = struct.unpack(array.array("B", msg[3:-1]).tostring())
            return AntCommand(msg_type, *msg_args)

    def send(self, command, timeout=DEFAULT_TIMEOUT):
        self.hardware.write(self.pack(command).extend([0, 0]))

    def recv(self, timeout=DEFAULT_TIMEOUT):
        while True:
            for msg in tokenize_message(self.hardware.read(timeout=timeout)):
                yield self.unpack(msg)
        

class AntDispatcher(object):
    
    def __init__(self):
        pass

    def start(self):
        pass

    def stop(self):
        pass


# vim: ts=4 sts=4 et
