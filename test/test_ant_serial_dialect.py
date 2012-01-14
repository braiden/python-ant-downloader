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

    def test_create_matcher(self):
        matcher = self.dialect._create_matcher(ANT_RESET_SYSTEM, ())
        self.assertTrue(matcher is None)
        DevMsgReq = collections.namedtuple("DevMsgReq", "message_id")
        ChanMsgReq = collections.namedtuple("ChanMsgReq", "message_id, channel_number")
        matcher = self.dialect._create_matcher(ANT_REQUEST_MESSAGE, DevMsgReq(ANT_VERSION))
        self.assertEquals(matcher.msg_id, ANT_VERSION)
        self.assertFalse(len(matcher.restrictions))
        matcher = self.dialect._create_matcher(ANT_REQUEST_MESSAGE, ChanMsgReq(ANT_CHANNEL_STATUS, 2))
        self.assertEquals(matcher.msg_id, ANT_CHANNEL_STATUS)
        self.assertEquals(matcher.restrictions, {"channel_number": 2})

    def test_create_validator(self):
        matcher = self.dialect._create_validator(ANT_OPEN_CHANNEL, ())
        self.assertEquals(matcher.msg_id, ANT_CHANNEL_RESPONSE_OR_EVENT)
        self.assertEquals(matcher.restrictions, {"message_code": 0})

    def test_zero_timeout_adds_no_listener(self):
        self.dialect._exec(0x43, "BH", (1, 0x23ad), 0)
        self.assertTrue(self.dialect._result_matchers.is_empty())


class TestApiResponseMatcher(unittest.TestCase):
    
    def test_match(self):
        msg1 = (0x40, collections.namedtuple("Message", "message_code")(0x21))
        msg2 = (0x40, collections.namedtuple("Message", "message_code")(0x20))
        self.assertFalse(ApiResponseMatcher(0x41).match(msg1))
        self.assertTrue(ApiResponseMatcher(0x40).match(msg1))
        self.assertFalse(ApiResponseMatcher(0x40, message_code=0x20).match(msg1))
        self.assertTrue(ApiResponseMatcher(0x40, message_code=0x20).match(msg2))


class TestMatchingListener(unittest.TestCase):

    def setUp(self):
        self.key = {"msg_id": "test", "channel_number": -1}
        self.dialect = mock.Mock()
        self.dialect.unpack.return_value = (0x00, (1,2,3))
        self.group = mock.Mock()
        self.true_matcher = mock.Mock()
        self.true_matcher.match.return_value = True
        self.false_matcher = mock.Mock()
        self.false_matcher.match.return_value = False
        self.listener = MatchingListener(self.key, self.dialect, self.true_matcher, self.true_matcher, 5000)

    def test_on_event_is_matched(self):
        self.listener._matcher = self.true_matcher
        self.listener._validator = self.true_matcher
        self.listener.on_event("", self.group)
        self.assertEquals(self.listener._result, (1,2,3))
        self.assertFalse(self.listener.is_running())
        self.group.remove_listener.assert_called_with(self.listener)

    def test_on_event_is_unmatched(self):
        self.listener._matcher = self.false_matcher
        self.listener._validator = self.true_matcher
        self.listener.on_event("", self.group)
        self.assertEquals(self.listener._result, None)
        self.assertTrue(self.listener.is_running())
        self.assertTrue(self.group.remove_listener.called is False)

    def test_on_event_is_failed(self):
        self.listener._matcher = self.true_matcher
        self.listener._validator = self.false_matcher
        self.listener.on_event("", self.group)
        self.assertEquals(self.listener._result, None)
        self.assertEquals(True, self.listener._exception)
        self.assertFalse(self.listener.is_running())
        self.group.remove_listener.assert_called_with(self.listener)

    def test_on_event_timeout(self):
        self.listener._expiration = 0
        self.listener.on_event("", self.group)
        self.assertEquals(self.listener._result, None)
        self.assertEquals(self.listener._exception, False)
        self.assertFalse(self.listener.is_running())
        self.group.remove_listener.assert_called_with(self.listener)

    def test_zero_timeout_is_not_running(self):
        listener = MatchingListener(self.key, self.dialect, self.true_matcher, self.true_matcher, 0)
        self.assertFalse(listener.is_running())


class TestListenerGroup(unittest.TestCase):

    def setUp(self):
        self.group = ListenerGroup()

    def test_remove_listener(self):
        l = mock.Mock()
        self.group.add_listener(l)
        self.group.remove_listener(l)
        self.group.on_event("test")
        self.assertTrue(l.on_event.called is False)

    def test_allow_duplicates(self):
        l = mock.Mock()
        self.group.allow_duplicates = True
        self.group.add_listener(l)
        self.group.add_listener(l)
        self.assertEquals(2, len(self.group._listeners))

    def test_dont_allow_duplicates(self):
        l = mock.Mock()
        self.group.allow_duplicates = False
        self.group.add_listener(l)
        try: self.group.add_listener(l)
        except: pass
        else: self.fail()
        self.assertEquals(1, len(self.group._listeners))

    def test_dont_dispatch_none(self):
        l = mock.Mock()
        self.group.propagate_none = False
        self.group.add_listener(l)
        self.group.on_event(None)
        self.assertTrue(l.on_event.called is False)

    def test_dispatch_none(self):
        l = mock.Mock()
        self.group.propagate_none = True
        self.group.add_listener(l)
        self.group.on_event(None)
        self.assertTrue(l.on_event.called is True)

    def test_dispatch_order(self):
        listeners = [mock.Mock() for n in range(0,10)]
        for listener in listeners:
            listener.on_event.return_value = False
            self.group.add_listener(listener)
        listeners[5].on_event.return_value = True
        self.group.on_event("")
        for (idx, listener) in enumerate(listeners):
            self.assertTrue(idx > 5 or listener.on_event.called)


class TestDispacther(unittest.TestCase):

    def test_run(self):
        hardware = mock.Mock()
        hardware.read.return_value = "\xa4\x01\x00\00\x00" * 5
        dispatcher = Dispatcher(hardware)
        class Listener(object):
            def on_event(inner, event):
                dispatcher._stopped = True
                self.assertEquals("\xa4\x01\x00\00\x00", event)
        dispatcher.listener = Listener()
        dispatcher.run()


# vim: et ts=4 sts=4
