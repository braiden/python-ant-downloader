import unittest
import mock

from gant.ant_workflow import *

class TestWorkflow(unittest.TestCase):

    def test_enter_transitions_multiple_states(self):
        s1 = mock.Mock()
        s2 = mock.Mock()
        s3 = mock.Mock()
        s1.enter.return_value = s2
        s2.enter.return_value = s3
        s3.enter.return_value = None
        wf = Workflow(s1)
        self.assertEquals(wf.enter(None, None), None)
        self.assertEquals(wf.state, s3)
        s1.enter.assert_called_with(None, None)
        s2.enter.assert_called_with(None, s1)
        s3.enter.assert_called_with(None, s2)
        
    def test_final_state(self):
        s1 = mock.Mock()
        s1.accept.return_value = FINAL_STATE
        s2 = mock.Mock()
        wf = Workflow(s1)
        wf.next_state = s2
        self.assertEquals(wf.accept(None, None), s2)

    def test_state_requests_reentry(self):
        s1 = mock.Mock()
        s1.accept.return_value = s1
        s1.enter.return_value = None
        wf = Workflow(s1)
        self.assertEquals(wf.accept(None, None), None)
        self.assertEquals(wf.state, s1)
        s1.accept.assert_called_with(None, None)
        s1.enter.assert_called_with(None, s1)


# vim: et ts=4 sts=4
