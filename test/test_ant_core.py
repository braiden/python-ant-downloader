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

import unittest
import mock

from gant.ant_core import *

class TestFunctions(unittest.TestCase):

    def test_generate_checkum(self):
        self.assertEquals(0xff, generate_checksum("\xa5\x5a"))
        self.assertEquals(0x00, generate_checksum("\xa5\x5a\xff"))

    def test_validate_checksum(self):
        self.assertTrue(validate_checksum("\xa5\x5a\xff"))
        self.assertTrue(validate_checksum("\xa5\x5a\xff\x00"))
        self.assertFalse(validate_checksum("\xa5\x5a\xff\x01"))        

    def test_tokenize(self):
        self.assertEquals(tokenize_message(None), [])
        self.assertEquals(tokenize_message("\xa4\x01\x00\x00\x00"), ["\xa4\x01\x00\x00\x00"])
        self.assertEquals(
            tokenize_message(
                "\xa4\x01\x01\x00\x00" +
                "\xa4\x01\x02\x00\x00" +
                "\xa4\x01\x03\x00\x00" + 
                "\xa4\x01\x04\x00\x00" +
                "\xa4\x01\x05\x00\x00" +
                "\xa4\x01\x06\x00\x00"),
            [   "\xa4\x01\x01\x00\x00",
                "\xa4\x01\x02\x00\x00",
                "\xa4\x01\x03\x00\x00",
                "\xa4\x01\x04\x00\x00",
                "\xa4\x01\x05\x00\x00",
                "\xa4\x01\x06\x00\x00"])

    def test_value_of(self):
        self.assertEquals("VERSION", value_of(MessageType, MessageType.VERSION))
        self.assertEquals("TX", value_of(RadioEventType, RadioEventType.TX))


class TestMarshaller(unittest.TestCase):

    def setUp(self):
        self.m = Marshaller()

    def test_pack(self):
        self.assertEquals(
            "\xa4\x03\x42\x01\x20\x03\xc7",
            self.m.pack(0x42, (1, 0x20, 3)))
        self.assertEquals(
            "\xa4\x03\x43\x01\xce\x71\x5a",
            self.m.pack(0x43, (1, 0x71ce)))

    def test_unpack(self):
        (msg_id, msg_args) = self.m.unpack("\xa4\x06\x54\x08\x03\xff\xaa\xbb\x00\x13")
        self.assertEquals(0x54, msg_id)
        self.assertEquals(8, msg_args[0])
        self.assertEquals(3, msg_args[1])
        (msg_id, msg_args) = self.m.unpack("\xa4\x05\x51\x01\x02\x03\x04\x05\xf1")
        self.assertEquals(0x51, msg_id)
        self.assertEquals(0x0302, msg_args[1])


class TestDispatcher(unittest.TestCase):

    def test_run(self):
        hardware = mock.Mock()
        marshaller = mock.Mock()
        hardware.read.return_value = None
        dispatcher = Dispatcher(hardware, marshaller)
        hardware.read.return_value = "\xa4\x01\x00\00\x00" * 5
        marshaller.unpack.return_value = "test"
        class Listener(object):
            n = 0
            msg = None
            def on_message(self, dispatcher, msg):
                self.msg = msg
                self.n += 1
                return self.n == 5 and None
        result = dispatcher.loop(Listener())
        self.assertEquals(5, result.n)
        self.assertEquals("test", result.msg)


# vim: et ts=4 sts=4
