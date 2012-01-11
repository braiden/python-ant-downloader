import unittest
import mock

from gant.ant_api import *

class TestDevice(unittest.TestCase):

    def setUp(self):
        self.dialect = mock.Mock()
        self.dialect.get_capabilities().result.max_channels = 8
        self.dialect.get_capabilities().result.max_networks = 3
        self.device = Device(self.dialect)

    def test_reset_device(self):
        self.device.reset_system()
        self.assertEquals(3, len(self.device.networks))
        self.assertEquals(8, len(self.device.channels))
        self.dialect.reset_system.assert_called_with()


class TestNetwork(unittest.TestCase):
    
    def setUp(self):
        self.dialect = mock.Mock()
        self.network = Network(0, self.dialect)

    def test_set_network_id(self):
        self.network.network_key = "TESTTEST"
        self.dialect.set_network_key.assert_called_with(0, "TESTTEST")


class TestChannel(unittest.TestCase):

    def setUp(self):
        self.dialect = mock.Mock()
        self.chan = Channel(3, self.dialect)
        self.net = Network(1, self.dialect)

    def test_open_channel(self):
        self.chan.network = self.net
        self.chan.channel_type = 0x20
        self.chan.device_number = 0xcd21
        self.chan.device_type = 0x04
        self.chan.trans_type = 0x15
        self.chan.period = 0x1000
        self.chan.search_timeout = 0x7F
        self.chan.rf_freq = 55
        self.chan.open()
        self.dialect.assign_channel.assert_called_with(3, 0x20, 1)
        self.dialect.set_channel_id.assert_called_with(3, 0xcd21, 0x04, 0x15)
        self.dialect.set_channel_period.assert_called_with(3, 0x1000)
        self.dialect.set_channel_search_timeout.assert_called_with(3, 0x7F)
        self.dialect.set_channel_rf_freq.assert_called_with(3, 55)
        self.dialect.open_channel.assert_called_with(3)
        
    def test_close_channel(self):
        self.chan.close()
        self.dialect.close_channel.assert_called_with(3)
        self.dialect.unassign_channel.assert_called_with(3)


# vim: et ts=4 sts=4
