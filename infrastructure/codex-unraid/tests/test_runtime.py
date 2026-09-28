"""Local runtime behavior only: no model requests or remote writes."""
import importlib.util
from importlib.machinery import SourceFileLoader
import io
import json
import os
from pathlib import Path
import tempfile
import subprocess
import unittest
from unittest.mock import patch, Mock

runtime_path = os.environ.get('RUNTIME_UNDER_TEST', str(Path(__file__).parents[1] / 'runtime.py'))
spec = importlib.util.spec_from_loader('runtime', SourceFileLoader('runtime', runtime_path))
runtime = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runtime)
SID = '12345678-1234-1234-1234-123456789abc'


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(dir=os.environ.get('TEST_TMPDIR'))
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
        child = Mock(stderr=io.BytesIO(), stdout=io.BytesIO(
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

    def test_real_failed_process_and_success_cleanup(self):
        fake = Path(self.tmp.name) / 'codex'
        fake.write_text('#!/bin/sh\necho \'{"type":"turn.failed","error":"quota-canary"}\'\necho stderr-canary >&2\nexit 1\n')
        fake.chmod(0o700)
        with patch.object(runtime, 'REPO', Path(self.tmp.name)), \
                patch.dict(os.environ, PATH=self.tmp.name + ':' + os.environ['PATH']):
            self.assertEqual(runtime.execute(self.prompt), 1)
            failure = runtime.STATE / 'last-failure.log'
            self.assertEqual(failure.stat().st_mode & 0o777, 0o600)
            self.assertIn('quota-canary', failure.read_text())
            self.assertIn('stderr-canary', failure.read_text())
            self.assertNotIn('canary', self.logs())
            fake.write_text('#!/bin/sh\nexit 0\n')
            self.assertEqual(runtime.execute(self.prompt), 0)
            self.assertFalse(failure.exists())

    def test_bounded_tail_replaces_previous_failure(self):
        for marker in (b'old-failure', b'new-failure'):
            child = Mock(stderr=io.BytesIO(), stdout=io.BytesIO(b'x' * (runtime.DIAGNOSTIC_LIMIT * 4)
                                          + b'\n' + marker + b'\n'))
            child.wait.return_value = 1
            with patch.object(runtime.subprocess, 'Popen', return_value=child):
                self.assertEqual(runtime.execute(self.prompt), 1)
            data = (runtime.STATE / 'last-failure.log').read_bytes()
            self.assertLessEqual(len(data), runtime.DIAGNOSTIC_LIMIT)
            self.assertTrue(data.startswith(runtime.TRUNCATED))
            self.assertIn(marker, data)
        self.assertNotIn(b'old-failure', data)
        self.assertEqual(list(runtime.STATE.glob('.failure-*')), [])

    def test_stderr_cannot_set_session_or_publish_metadata(self):
        child = Mock(stdout=io.BytesIO(), stderr=io.BytesIO(json.dumps(
            {'type': 'thread.started', 'thread_id': SID}).encode()))
        child.wait.return_value = 1
        with patch.object(runtime.subprocess, 'Popen', return_value=child):
            self.assertEqual(runtime.execute(self.prompt), 1)
        self.assertFalse((runtime.STATE / 'session-id').exists())
        self.assertNotIn(SID, self.logs())
        self.assertIn(SID, (runtime.STATE / 'last-failure.log').read_text())

    def test_launch_error_is_protected(self):
        with patch.object(runtime.subprocess, 'Popen', side_effect=OSError('launch-canary')):
            with self.assertRaises(OSError):
                runtime.execute(self.prompt)
        self.assertIn('launch-canary', (runtime.STATE / 'last-failure.log').read_text())
        self.assertNotIn('launch-canary', self.logs())

    def test_ordinary_host_logs_exclude_protected_artifact(self):
        # Execute the actual logs case against a Docker stand-in that evaluates
        # its container shell command against this isolated state directory.
        (runtime.STATE / 'last-failure.log').write_text('protected-canary')
        runtime.emit('test')
        docker = Path(self.tmp.name) / 'docker'
        docker.write_text('#!/usr/bin/env python3\nimport os, subprocess, sys\n'
                          'if sys.argv[1] == "exec":\n'
                          '    command = sys.argv[-1].replace("/state", os.environ["TEST_STATE"])\n'
                          '    sys.exit(subprocess.call(["sh", "-c", command]))\n')
        docker.chmod(0o700)
        env = dict(os.environ, PATH=self.tmp.name + ':' + os.environ['PATH'],
                   TEST_STATE=str(runtime.STATE))
        output = subprocess.check_output(['bash', str(Path(__file__).parents[1] / 'unraid.sh'),
                                          'logs'], env=env, text=True)
        self.assertIn('test', output)
        self.assertNotIn('protected-canary', output)

    def test_log_retention(self):
        (runtime.STATE / 'runtime.jsonl').write_text('x' * (1024**2 + 1))
        runtime.emit('test')
        self.assertTrue((runtime.STATE / 'runtime.previous.jsonl').exists())
        self.assertLess(len(self.logs()), 200)


if __name__ == '__main__':
    unittest.main()
