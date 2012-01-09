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
        self.assertEquals(8, self.device.availible_channels)
        self.assertEquals(3, self.device.availible_networks)
        self.assertEquals(8, self.device.max_channels)
        self.assertEquals(3, self.device.max_networks)

    def test_claim_channel(self):
        channels = []
        for n in range(0, self.device.max_channels):
            c = self.device.claim_channel()
            self.assertTrue(c)
            self.assertTrue(c.is_valid())
            channels.append(c)
        self.assertEquals(self.device.availible_channels, 0)
        for (n, c) in enumerate(channels):
            self.device.release_channel(c)
            self.assertEquals(n + 1, self.device.availible_channels)
        with self.device.channel() as c:
            self.assertTrue(c.is_valid())
        self.assertEquals(self.device.availible_channels, 8)

    def test_claim_network(self):
        networks = []
        for n in range(0, self.device.max_networks):
            c = self.device.claim_network()
            self.assertTrue(c)
            self.assertTrue(c.is_valid())
            networks.append(c)
        self.assertEquals(self.device.availible_networks, 0)
        for (n, c) in enumerate(networks):
            self.device.release_network(c)
            self.assertEquals(n + 1, self.device.availible_networks)
        with self.device.network() as c:
            self.assertTrue(c.is_valid())
        self.assertEquals(self.device.availible_networks, 3)


class TestNetwork(unittest.TestCase):
    
    def setUp(self):
        self.dialect = mock.Mock()
        self.device = mock.Mock()
        self.network = Network(0, self.device, self.dialect)

    def test_set_network_id(self):
        self.network.network_key = "TESTTEST"
        self.dialect.set_network_key.assert_called_with(0, "TESTTEST")
        self.device.is_valid_network.return_value = False
        try: self.network.network_key = "TESTTEST"
        except: pass
        else: self.fail("Attempt to set key on invalid network should fail.")


class TestFuture(unittest.TestCase):

    def test_future(self):
        f = Future()
        f.timeout = .1
        try: f.wait()
        except: pass
        else: self.fail("Timeout shoud raise.")
        f = Future()
        f.set_exception(IndexError())
        try: f.wait()
        except IndexError: pass
        else: self.fail("Exception should be rethrown.")
        f = Future()
        f.result = 1
        self.assertEquals(1, f.result)


class TestChannel(unittest.TestCase):

    def setUp(self):
        self.dialect = mock.Mock()
        self.device = mock.Mock()
        self.chan = Channel(3, self.device, self.dialect)
        self.net = Network(1, self.device, self.dialect)

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
