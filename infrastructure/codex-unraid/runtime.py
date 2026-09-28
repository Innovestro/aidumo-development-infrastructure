#!/usr/bin/env python3
"""One explicitly invoked executor. No discovery, dispatch, queue or auto-resume."""
import fcntl
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import sys
import threading
import tempfile
import traceback
import time

STATE = Path('/state')
WORK = Path('/workspace')
REPO = WORK / 'aidumo-development-infrastructure'
CODEX = Path('/codex')
SECRETS = Path('/run/secrets')
LOG_LOCK = threading.Lock()
SESSION_ID = r'[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}'
DIAGNOSTIC_LIMIT = 256 * 1024
TRUNCATED = b"[truncated: retaining final diagnostic bytes]\n"

LIMIT = 10 * 1024**3  # Admission ceiling; owner filesystem supplies the hard cap.


def emit(event, **fields):
    line = json.dumps(dict(time=int(time.time()), event=event, **fields))
    with LOG_LOCK:
        log = STATE / 'runtime.jsonl'
        if log.exists() and log.stat().st_size > 1024**2:
            log.replace(STATE / 'runtime.previous.jsonl')
        with log.open('a') as stream:
            stream.write(line + '\n')


def storage_bytes():
    return sum(int(subprocess.check_output(
        ['du', '-s', '-B1', str(p)], text=True).split()[0])
        for p in (WORK, CODEX, STATE))


def sample():
    """Numeric cgroup v2 measurements, no process arguments or file contents."""
    root = Path('/sys/fs/cgroup')
    try:
        cpu = dict(line.split() for line in (root / 'cpu.stat').read_text().splitlines())
        return dict(cpu_usec=int(cpu['usage_usec']),
                    memory_bytes=int((root / 'memory.current').read_text()),
                    pids=int((root / 'pids.current').read_text()))
    except (OSError, KeyError, ValueError):
        return {}  # Host docker stats remains required on cgroup v1.


def safe_event(event):
    """Allowlist metadata. Never forward model text, tool output or error strings."""
    kind = event.get('type')
    if kind == 'thread.started':
        sid = event.get('thread_id', '')
        if isinstance(sid, str) and re.fullmatch(SESSION_ID, sid):
            (STATE / 'session-id').write_text(sid + '\n')
            emit('session', session_id=sid)
    elif kind in ('turn.completed', 'turn.failed'):
        emit(kind)


class FailureTail:
    """Bound memory and disk independently of invocation output size."""
    def __init__(self):
        self.tail = bytearray()
        self.truncated = False
        self.lock = threading.Lock()

    def append(self, data):
        with self.lock:
            self.tail.extend(data)
            capacity = DIAGNOSTIC_LIMIT - len(TRUNCATED)
            if len(self.tail) > capacity:
                del self.tail[:-capacity]
                self.truncated = True

    def finish(self, rc):
        target = STATE / 'last-failure.log'
        if rc == 0:
            target.unlink(missing_ok=True)
            return
        # mkstemp is 0600 even when execute is imported without main's umask.
        fd, name = tempfile.mkstemp(prefix='.failure-', dir=STATE)
        try:
            with os.fdopen(fd, 'wb') as stream:
                if self.truncated:
                    stream.write(TRUNCATED)
                stream.write(self.tail)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(name, target)
        finally:
            Path(name).unlink(missing_ok=True)


def execute(prompt, resume=False):
    with (STATE / 'executor.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return 75
        if (STATE / 'drain').exists():
            emit('refused_drained')
            return 75
        size = storage_bytes()
        if size >= LIMIT or shutil.disk_usage(WORK).free < 1024**3:
            emit('refused_storage', storage_bytes=size)
            return 73
        (STATE / 'exit-code').unlink(missing_ok=True)
        (STATE / 'task.md').write_bytes(prompt.read_bytes())
        # Read only the dedicated PR token. No inherited Owner credentials.
        env = dict(os.environ)
        env['GH_TOKEN'] = (SECRETS / 'gh_token').read_text().strip()
        if not env['GH_TOKEN']:
            return 78
        args = ['codex', 'exec', '--json']
        if resume:
            sid = (STATE / 'session-id').read_text().strip()
            if not re.fullmatch(SESSION_ID, sid):
                return 78
            args += ['resume', sid]
        args += ['-']
        stopped = threading.Event()
        def measure():
            while not stopped.wait(5):
                emit('resources', **sample())
        emit('started', storage_bytes=size, **sample())
        monitor = threading.Thread(target=measure, daemon=True)
        monitor.start()
        rc = 70
        diagnostic = FailureTail()
        try:
            with prompt.open('rb') as source:
                child = subprocess.Popen(args, cwd=REPO, env=env, stdin=source,
                                         stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            # Keep stderr out of the JSON parser so it cannot corrupt session
            # events or masquerade as allowlisted metadata. Drain concurrently.
            def capture_stderr():
                with child.stderr:
                    while True:
                        chunk = child.stderr.read(65536)
                        if not chunk:
                            break
                        diagnostic.append(chunk)
            errors = threading.Thread(target=capture_stderr, daemon=True)
            errors.start()
            def interrupt(signum, _frame):
                child.send_signal(signum)
            signal.signal(signal.SIGTERM, interrupt)
            signal.signal(signal.SIGINT, interrupt)
            # Bound individual output lines; oversized content is discarded in chunks.
            while True:
                line = child.stdout.readline(65537)
                diagnostic.append(line)
                if not line:
                    break
                if len(line) > 65536:
                    while line and not line.endswith(b'\n'):
                        line = child.stdout.readline(65537)
                        diagnostic.append(line)
                    continue
                try:
                    event = json.loads(line)
                    if isinstance(event, dict):
                        safe_event(event)
                except (ValueError, UnicodeDecodeError):
                    pass
            child.stdout.close()
            rc = child.wait()
            errors.join()
        except Exception:
            diagnostic.append(traceback.format_exc().encode())
            raise
        finally:
            stopped.set()
            monitor.join()
            diagnostic.append(('\n[executor exit %s]\n' % rc).encode())
            diagnostic.finish(rc)
            emit('finished', exit_code=rc, storage_bytes=storage_bytes(), **sample())
            (STATE / 'exit-code').write_text(str(rc) + '\n')
        return rc


def main():
    os.umask(0o077)
    command = sys.argv[1] if len(sys.argv) > 1 else 'idle'
    if command == 'idle':
        # Always start drained, including after an unexpected host reboot.
        (STATE / 'drain').touch()
        shutil.copyfile('/opt/codex/config.toml', CODEX / 'config.toml')
        print('Runtime ready; drained. No task starts automatically.', flush=True)
        while True:
            time.sleep(3600)
    if command in ('run', 'resume') and len(sys.argv) == 3:
        return execute(Path(sys.argv[2]), command == 'resume')
    raise ValueError('usage: runtime idle | run PROMPT | resume PROMPT')


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception:
        # Details may include tool output or credential paths; keep ordinary logs clean.
        print('Runtime failed; inspect protected state locally.', file=sys.stderr)
        sys.exit(70)
