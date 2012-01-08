import unittest
import mock
import collections

from gant.ant_serial_dialect import *

class TestSerialDialect(unittest.TestCase):

    def setUp(self):
        self.hardware = mock.Mock()
        self.dispatcher = mock.Mock()
        self.dialect = SerialDialect(self.hardware, self.dispatcher)

    def test_exec(self):
        self.dialect._exec(
            0x42, "BBB", collections.namedtuple("assignChannel", "channel_number, channel_type, network_number"),
            1, network_number=3, channel_type=0x20)
        self.hardware.write.assert_called_with("\xa4\x03\x42\x01\x20\x03\xc7")

    def test_generate_checkum(self):
        self.assertEquals(0xff, self.dialect.generate_checksum("\xa5\x5a"))
        self.assertEquals(0x00, self.dialect.generate_checksum("\xa5\x5a\xff"))

    def test_validate_checksum(self):
        self.assertTrue(self.dialect.validate_checksum("\xa5\x5a\xff"))
        self.assertTrue(self.dialect.validate_checksum("\xa5\x5a\xff\x00"))
        self.assertFalse(self.dialect.validate_checksum("\xa5\x5a\xff\x01"))        

    def test_enhanced_method(self):
        self.dialect.reset_system()
        self.hardware.write.assert_called_with("\xa4\x01\x4a\x00\xef")
        
    def test_unpack(self):
        (msg_id, msg_args) = self.dialect.unpack("\xa4\x06\x54\x08\x03\xff\xaa\xbb\x00\x13")
        self.assertEquals(0x54, msg_id)
        self.assertEquals(3, msg_args.max_networks)
        self.assertEquals(8, msg_args.max_channels)


class TestMessageMatcher(unittest.TestCase):
    
    def test_match(self):
        ChannelEvent = collections.namedtuple("ChannelEvent", "channel_number, message_id, message_code")
        dialect = mock.Mock()
        dialect.unpack.return_value = (0x40, ChannelEvent(0x00, 0x51, 0x00))
        self.assertFalse(MessageMatcher(dialect, 0x41).match(None))
        self.assertTrue(MessageMatcher(dialect, 0x40).match(None))
        self.assertFalse(MessageMatcher(dialect, 0x40, message_code=0x20).match(None))


class TestMatchingListener(unittest.TestCase):

    def test_event(self):
        dispatcher = mock.Mock()
        matcher = mock.Mock()
        matcher.match.return_value = False
        l = MatchingListener(matcher)
        self.assertFalse(l.is_matched_event.is_set())
        l.on_message(dispatcher, None)
        self.assertFalse(l.is_matched_event.is_set())
        self.assertFalse(dispatcher.remove_listener.called)
        matcher.match.return_value = True
        l.on_message(dispatcher, None)
        self.assertTrue(l.is_matched_event.is_set())
        self.assertTrue(dispatcher.remove_listener.called)


class TestDispatcher(unittest.TestCase):

    def setUp(self):
        self.hardware = mock.Mock()
        self.dispatcher = Dispatcher(self.hardware)

    def test_add_listeners(self):
        l1 = mock.Mock()
        l2 = mock.Mock()
        self.dispatcher.add_listener(l1)
        self.dispatcher.add_listener(l2)
        self.hardware.read.return_value = "TEST"
        self.dispatcher.start()
        self.dispatcher.stop().join()
        l1.on_message.assert_called_with(self.dispatcher, "TEST")
        l2.on_message.assert_called_with(self.dispatcher, "TEST")

    def test_remove_listener(self):
        l = mock.Mock()
        self.dispatcher.add_listener(l)
        self.dispatcher.remove_listener(l)
        self.dispatcher.start()
        self.dispatcher.stop().join()
        self.assertFalse(l.on_message.called)


# vim: et ts=4 sts=4
