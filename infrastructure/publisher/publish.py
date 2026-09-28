#!/usr/bin/env python3
"""Publish one new B branch/PR; remote evidence is the replay identity."""
import argparse
import json
from pathlib import Path
import re
import subprocess
import sys

REPO = 'Innovestro/aidumo-development-infrastructure'
REMOTE = 'git@github.com:' + REPO + '.git'


class Blocked(RuntimeError):
    pass


def command(args):
    result = subprocess.run(args, capture_output=True, text=True, timeout=60)
    if result.returncode:
        raise Blocked('command_failed_reconcile_remote_before_retry')
    return result.stdout.strip()


class Remote:
    def head(self, branch):
        rows = command(['git', 'ls-remote', 'origin', 'refs/heads/' + branch]).splitlines()
        if len(rows) > 1:
            raise Blocked('ambiguous_remote_branch')
        return rows[0].split()[0] if rows else None

    def prs(self, branch):
        rows = json.loads(command(['gh', 'api', '--method', 'GET',
            f'repos/{REPO}/pulls?state=all&head=Innovestro:{branch}&per_page=100']))
        if not isinstance(rows, list) or len(rows) >= 100:
            raise Blocked('incomplete_pr_inventory')
        return rows

    def push_new(self, branch, head):
        # An absent-ref lease is the single creator fence, also across processes.
        command(['git', 'push', '--force-with-lease=refs/heads/' + branch + ':',
                 'origin', head + ':refs/heads/' + branch])

    def create(self, branch, body_file, title):
        command(['gh', 'pr', 'create', '--repo', REPO, '--base', 'main',
                 '--head', branch, '--title', title, '--body-file', str(body_file)])


def existing(rows, issue, branch, head):
    if len(rows) != 1:
        raise Blocked('multiple_prs' if rows else 'branch_without_pr_unknown_outcome')
    pr = rows[0]
    if (pr['head']['sha'] != head or pr['head']['ref'] != branch
            or pr['head']['repo']['full_name'] != REPO or pr['base']['ref'] != 'main'
            or pr['base']['repo']['full_name'] != REPO
            or not re.search(r'(?im)^Closes #' + str(issue) + r'\s*$', pr.get('body') or '')):
        raise Blocked('conflicting_pr_identity')
    return dict(result='published', pr=pr['number'], url=pr['html_url'], head=head)


def publish(remote, issue, branch, head, body_file, title):
    observed = remote.head(branch)
    rows = remote.prs(branch)
    if rows:
        if observed not in (None, head):
            raise Blocked('remote_head_changed')
        return existing(rows, issue, branch, head)
    if observed is not None:
        raise Blocked('branch_without_pr_unknown_outcome')
    # Only the invocation that successfully creates the absent branch may make
    # one PR-create attempt. A restart with only the branch always stops.
    remote.push_new(branch, head)
    if remote.head(branch) != head:
        raise Blocked('remote_head_changed')
    rows = remote.prs(branch)
    if rows:
        return existing(rows, issue, branch, head)
    try:
        remote.create(branch, body_file, title)
    except (Blocked, subprocess.TimeoutExpired):
        # The response may have been lost after GitHub committed the operation.
        # Reading is safe; absence never authorizes another create attempt.
        return existing(remote.prs(branch), issue, branch, head)
    return existing(remote.prs(branch), issue, branch, head)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--issue', required=True, type=int)
    parser.add_argument('--branch', required=True)
    parser.add_argument('--head', required=True)
    parser.add_argument('--body-file', required=True, type=Path)
    parser.add_argument('--title', required=True)
    args = parser.parse_args()
    try:
        if (args.issue <= 0 or not re.fullmatch(r'codex/' + str(args.issue) + r'-[a-z0-9-]+', args.branch)
                or not re.fullmatch('[0-9a-f]{40}', args.head)):
            raise Blocked('invalid_explicit_identity')
        if command(['git', 'remote', 'get-url', 'origin']) != REMOTE:
            raise Blocked('not_b_repository_transport')
        if command(['git', 'rev-parse', 'HEAD']) != args.head:
            raise Blocked('local_head_mismatch')
        if command(['git', 'status', '--porcelain']):
            raise Blocked('dirty_checkout')
        body = args.body_file.read_text()
        if not re.search(r'(?im)^Closes #' + str(args.issue) + r'\s*$', body):
            raise Blocked('missing_owning_issue_reference')
        result = publish(Remote(), args.issue, args.branch, args.head, args.body_file, args.title)
        print(json.dumps(result, sort_keys=True))
        return 0
    except (Blocked, OSError, ValueError, KeyError, TypeError, subprocess.TimeoutExpired) as exc:
        print(json.dumps(dict(result='blocked', reason=str(exc) if isinstance(exc, Blocked)
                              else 'unavailable_or_invalid_evidence', retry_authorized=False)))
        return 2


if __name__ == '__main__':
    sys.exit(main())
