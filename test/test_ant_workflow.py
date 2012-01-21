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
    state.next_state = FINAL_STATE
    return state

def fail(self, *args, **kwd):
    raise AssertionError()

def default(self, *args, **kwd):
    pass


class TestRetry(unittest.TestCase):

    def test_retry_failing_enter(self):
        ctx = mock_context()
        s = mock_state()
        s.enter = fail
        retry = Retry(s, retry_count=1)
        self.assertEquals(retry, retry.enter(ctx))
        try: retry.enter(ctx)
        except AssertionError as e:
            pass
        else:
            self.fail()

    def test_retry_count_resets_on_succes(self):
        ctx = mock_context()
        s = mock_state()
        s.enter = fail
        retry = Retry(s, retry_count=1)
        retry.enter(ctx);
        self.assertEquals(1, retry.failed_count)
        s.enter = default
        retry.enter(ctx)
        self.assertEquals(1, retry.failed_count)
        retry.accept(ctx, None)
        self.assertEquals(0, retry.failed_count)
        s.enter = fail
        retry.enter(ctx)
        self.assertEquals(1, retry.failed_count)

    def test_fail_on_accept(self):
        ctx = mock_context()
        s = mock_state()
        s.enter = fail
        s.accept = fail
        retry = Retry(s, retry_count=2)
        retry.enter(ctx);
        self.assertEquals(1, retry.failed_count)
        s.enter = default
        retry.enter(ctx)
        self.assertEquals(1, retry.failed_count)
        self.assertEquals(retry, retry.accept(ctx, None))
        try:
            retry.accept(ctx, None)
        except AssertionError as e:
            pass
        else:
            self.fail()


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
