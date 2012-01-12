import unittest
import mock
import collections
import time

from gant.ant_serial_dialect import *
from gant.ant_api import *

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


class TestSerialDialect(unittest.TestCase):

    def setUp(self):
        self.hardware = mock.Mock()
        self.hardware.read.return_value = None
        self.dialect = SerialDialect(self.hardware)
        self.dialect._dispatcher.stop()

    def test_pack(self):
        self.dialect._exec(0x42, "BBB", (1, 0x20, 3), 0)
        self.hardware.write.assert_called_with("\xa4\x03\x42\x01\x20\x03\xc7\x00\x00")
        self.dialect._exec(0x43, "BH", (1, 0x71ce), 0)
        self.hardware.write.assert_called_with("\xa4\x03\x43\x01\xce\x71\x5a\x00\x00")

    def test_enhanced_method(self):
        self.dialect.reset_system()
        self.hardware.write.assert_called_with("\xa4\x01\x4a\x00\xef\x00\x00")
        
    def test_unpack(self):
        (msg_id, msg_args) = self.dialect.unpack("\xa4\x06\x54\x08\x03\xff\xaa\xbb\x00\x13")
        self.assertEquals(0x54, msg_id)
        self.assertEquals(3, msg_args.max_networks)
        self.assertEquals(8, msg_args.max_channels)
        (msg_id, msg_args) = self.dialect.unpack("\xa4\x05\x51\x01\x02\x03\x04\x05\xf1")
        self.assertEquals(0x51, msg_id)
        self.assertEquals(0x0302, msg_args.device_number)


class TestMessageMatcher(unittest.TestCase):
    
    def test_match(self):
        msg1 = (0x40, collections.namedtuple("Message", "message_code")(0x21))
        msg2 = (0x40, collections.namedtuple("Message", "message_code")(0x20))
        self.assertFalse(MessageMatcher(0x41).match(msg1))
        self.assertTrue(MessageMatcher(0x40).match(msg1))
        self.assertFalse(MessageMatcher(0x40, message_code=0x20).match(msg1))
        self.assertTrue(MessageMatcher(0x40, message_code=0x20).match(msg2))


class TestMatchingListener(unittest.TestCase):

    def test_event(self):
        dialect = mock.Mock()
        matcher = mock.Mock()
        validator = mock.Mock()
        group = mock.Mock()
        dialect.unpack.return_value = (0x00, ())
        matcher.match.return_value = False
        validator.return_value = True
        matching_listener = MatchingListener(0x00, dialect, matcher, validator, millis() + 2000)
        matching_listener.on_event("", group)
        self.assertTrue(matching_listener._result is None)
        self.assertFalse(matching_listener._exception)
        self.assertFalse(group.remove_listener.called)
        matcher.match.return_value = True
        matching_listener.on_event("", group)
        self.assertTrue(matching_listener._result is not None)
        self.assertFalse(matching_listener._exception)
        self.assertTrue(group.remove_listener.called)
        group.reset_mock()
        matching_listener = MatchingListener(0x00, dialect, matcher, validator, millis() + 2000)
        validator.match.return_value = False
        matching_listener.on_event("", group)
        self.assertTrue(matching_listener._result is None)
        self.assertTrue(matching_listener._exception)
        self.assertTrue(group.remove_listener.called)


class TestListenerGroup(unittest.TestCase):

    def setUp(self):
        self.group = ListenerGroup()

    def test_remove_listener(self):
        l = mock.Mock()
        self.group.add_listener(l)
        self.group.remove_listener(l)
        self.group.on_event("test")
        self.assertFalse(l.on_event.called)

    def test_dispatch_in_order_of_registration(self):
        listeners = [mock.Mock() for n in range(0,10)]
        for listener in listeners:
            listener.on_event.return_value = False
            self.group.add_listener(listener)
        listeners[5].on_event.return_value = True
        self.group.on_event("test")
        for (idx, listener) in enumerate(listeners):
            self.assertTrue(idx > 5 or listener.on_event.called)


# vim: et ts=4 sts=4
