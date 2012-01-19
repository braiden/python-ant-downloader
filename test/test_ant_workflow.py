import unittest
import mock

from gant.ant_workflow import *

def mock_context():
    ctx = Context(None, None)
    return ctx

def mock_state():
    state = mock.Mock()
    state.enter.return_value = None
    state.accept.return_value = FINAL_STATE
    return state


class TestWorkflow(unittest.TestCase):

    def test_enter_transitions_multiple_states(self):
        ctx = mock_context()
        s1 = mock_state()
        s2 = mock_state()
        s3 = mock_state()
        s1.enter.return_value = s2
        s2.enter.return_value = s3
        s3.enter.return_value = None
        wf = Workflow(s1)
        self.assertEquals(wf.enter(ctx), None)
        self.assertEquals(wf.state, s3)
        self.assertTrue(s1.enter.called is True)
        self.assertTrue(s2.enter.called is True)
        self.assertTrue(s3.enter.called is True)
        
    def test_final_state(self):
        ctx = mock_context()
        s1 = mock_state()
        s2 = mock_state()
        wf = Workflow(s1)
        wf.next_state = s2
        self.assertEquals(wf.enter(ctx), None)
        self.assertEquals(wf.state, s1)
        self.assertEquals(wf.accept(ctx, None), s2)

    def test_state_requests_reentry(self):
        ctx = mock_context()
        s1 = mock_state()
        s1.accept.return_value = s1
        wf = Workflow(s1)
        self.assertEquals(wf.enter(ctx), None)
        self.assertEquals(wf.accept(ctx, None), None)
        self.assertEquals(wf.state, s1)
        self.assertTrue(s1.enter.called is True)
        self.assertTrue(s1.enter.called is True)

    def test_workflow_is_state(self):
        ctx = mock_context()
        state = mock_state()
        state.accept.return_value = state
        w1 = Workflow(state)
        w2 = Workflow(w1)
        w3 = Workflow(w2)
        self.assertEquals(w3.enter(ctx), None)
        self.assertEquals(w3.accept(ctx, None), None)
        state.accept.return_value = FINAL_STATE
        self.assertEquals(w3.accept(ctx, None), FINAL_STATE)

    def test_workflow_context(self):
        ctx = mock_context()
        st1 = mock_state()
        st2 = mock_state()
        wf1 = Workflow(st1)
        wf1.next_state = st2
        st2.next_state = wf1
        wf1.enter(ctx)
        wf1_ctx = st1.enter.call_args[0][0]
        self.assertEquals(wf1_ctx.parent_context, ctx)
        self.assertEquals(wf1.accept(ctx, None), st2)
        st1.accept.assert_called_with(wf1_ctx, None)
        wf1.enter(ctx)
        self.assertFalse(wf1_ctx == st1.enter.call_args[0][0])


# vim: et ts=4 sts=4
