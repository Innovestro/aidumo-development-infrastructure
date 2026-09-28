"""Local runtime behavior only: no model requests or remote writes."""
import importlib.util
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch, Mock

spec = importlib.util.spec_from_file_location('runtime', Path(__file__).parents[1] / 'runtime.py')
runtime = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runtime)
SID = '12345678-1234-1234-1234-123456789abc'


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        for constant in ('STATE', 'WORK', 'CODEX', 'SECRETS'):
            path = root / constant
            path.mkdir()
            patcher = patch.object(runtime, constant, path)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.prompt = root / 'prompt.md'
        self.prompt.write_text('Only the admitted task')
        (runtime.SECRETS / 'gh_token').write_text('FAKE-SECRET-CANARY')
        self.addCleanup(patch.stopall)
        patch.object(runtime, 'sample', return_value={'cpu_usec': 1, 'memory_bytes': 2}).start()
        patch.object(runtime, 'storage_bytes', return_value=100).start()
        patch.object(runtime.shutil, 'disk_usage', return_value=Mock(free=2 * 1024**3)).start()
        patch.object(runtime.signal, 'signal').start()

    def logs(self):
        path = runtime.STATE / 'runtime.jsonl'
        return path.read_text() if path.exists() else ''

    def test_metadata_drops_all_text_and_malformed_session(self):
        for event in ({'type': 'item.completed', 'text': 'FAKE-SECRET-CANARY'},
                      {'type': 'error', 'message': 'FAKE-SECRET-CANARY'},
                      {'type': 'thread.started', 'thread_id': 123},
                      {'type': 'thread.started', 'thread_id': 'FAKE-SECRET-CANARY'}):
            runtime.safe_event(event)
        self.assertEqual(self.logs(), '')
        runtime.safe_event({'type': 'thread.started', 'thread_id': SID})
        self.assertEqual((runtime.STATE / 'session-id').read_text().strip(), SID)

    def test_drained_and_busy_never_invoke_codex(self):
        with patch.object(runtime.subprocess, 'Popen') as launch:
            (runtime.STATE / 'drain').touch()
            self.assertEqual(runtime.execute(self.prompt), 75)
            (runtime.STATE / 'drain').unlink()
            with (runtime.STATE / 'executor.lock').open('a') as lock:
                runtime.fcntl.flock(lock, runtime.fcntl.LOCK_EX | runtime.fcntl.LOCK_NB)
                self.assertEqual(runtime.execute(self.prompt), 75)
            launch.assert_not_called()

    def test_storage_budget_refuses_before_invocation(self):
        with patch.object(runtime, 'storage_bytes', return_value=runtime.LIMIT), \
                patch.object(runtime.subprocess, 'Popen') as launch:
            self.assertEqual(runtime.execute(self.prompt), 73)
            launch.assert_not_called()

    def test_resume_exact_id_and_nonzero_exit_preserved_without_raw_output(self):
        (runtime.STATE / 'session-id').write_text(SID)
        child = Mock(stdout=io.BytesIO(
            b'{"type":"item.completed","text":"FAKE-SECRET-CANARY"}\n'
            + b'x' * 70000 + b'\n'
            + json.dumps({'type': 'turn.failed', 'error': 'FAKE-SECRET-CANARY'}).encode() + b'\n'))
        child.wait.return_value = 9
        with patch.object(runtime.subprocess, 'Popen', return_value=child) as launch:
            self.assertEqual(runtime.execute(self.prompt, resume=True), 9)
            self.assertEqual(launch.call_args.args[0], ['codex', 'exec', '--json', 'resume', SID, '-'])
            self.assertEqual(launch.call_args.kwargs['env']['GH_TOKEN'], 'FAKE-SECRET-CANARY')
        self.assertEqual((runtime.STATE / 'task.md').read_text(), self.prompt.read_text())
        self.assertEqual((runtime.STATE / 'exit-code').read_text().strip(), '9')
        self.assertNotIn('FAKE-SECRET-CANARY', self.logs())
        self.assertIn('turn.failed', self.logs())

    def test_log_retention(self):
        (runtime.STATE / 'runtime.jsonl').write_text('x' * (1024**2 + 1))
        runtime.emit('test')
        self.assertTrue((runtime.STATE / 'runtime.previous.jsonl').exists())
        self.assertLess(len(self.logs()), 200)


if __name__ == '__main__':
    unittest.main()
