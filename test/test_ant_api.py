import unittest
import mock

from gant.ant_api import *
from gant.ant_workflow import *
import gant.ant_command as commands

class TestDevice(unittest.TestCase):

    def setUp(self):
        self.executor = mock.Mock()
        self.executor.execute().result = {
            'max_channels': 8,
            'max_networks': 3,
            'standard_options': 0,
            'advanced_options_1': 0,
            'advanced_options_2': 0,
        }
        self.device = Device(self.executor, commands)

    def test_reset_device(self):
        self.device.reset_system()
        self.assertEquals(3, len(self.device.networks))
        self.assertEquals(8, len(self.device.channels))


# vim: et ts=4 sts=4
