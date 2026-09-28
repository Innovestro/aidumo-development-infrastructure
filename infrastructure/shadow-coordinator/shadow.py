#!/usr/bin/env python3
"""One-shot read-only Suite observation. No stored state or execution authority."""
import argparse
import ast
import base64
import datetime as dt
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import types

REPO = 'Innovestro/aidumo-suite'
ROOT = f'repos/{REPO}'
PINS = json.loads(Path(__file__).with_name('contracts.json').read_text())


class Unknown(RuntimeError):
    pass


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'))


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def get(path):
    """Only fixed-repository REST GETs; never accept a URL or command from evidence."""
    if not path.startswith(ROOT + '/') or '..' in path or '#' in path:
        raise Unknown('invalid_read_path')
    result = subprocess.run(['gh', 'api', '--method', 'GET', path],
                            capture_output=True, text=True, timeout=45)
    if result.returncode:
        # Do not publish response bodies or credential-bearing diagnostics.
        raise Unknown('read_unavailable:' + path.split('?')[0])
    return json.loads(result.stdout)


def pages(path, key=None):
    rows = []
    for page in range(1, 21):
        value = get(f'{path}{"&" if "?" in path else "?"}per_page=100&page={page}')
        batch = value[key] if key else value
        if not isinstance(batch, list):
            raise Unknown('invalid_page')
        rows.extend(batch)
        if len(batch) < 100:
            return unique(rows)
    raise Unknown('bounded_read_limit')


def unique(rows):
    by_id = {}
    for row in rows:
        key = row['id']
        if key in by_id and row != by_id[key]:
            raise Unknown('conflicting_duplicate')
        by_id[key] = row
    return [by_id[key] for key in sorted(by_id)]


def resolver(sources):
    """Load only the reviewed pure prefix of Suite's exact canonical resolver.

    Network/CLI/writer definitions and their imports are never compiled. The
    full-file digest prevents upstream edits from changing this extraction.
    """
    for path, expected in PINS.items():
        if hashlib.sha256(sources[path]).hexdigest() != expected:
            raise Unknown('contract_drift:' + path)
    tree = ast.parse(sources['.github/scripts/work_claim.py'])
    imports = {'__future__', 'datetime', 're', 'dataclasses', 'typing'}
    nodes = []
    for node in tree.body:
        if node.lineno >= 741:
            break
        if isinstance(node, ast.Import):
            if all(alias.name in imports for alias in node.names):
                nodes.append(node)
        elif isinstance(node, ast.ImportFrom):
            if node.module in imports:
                nodes.append(node)
        elif isinstance(node, (ast.Assign, ast.ClassDef, ast.FunctionDef)):
            nodes.append(node)
    module = types.ModuleType('suite_shadow_claims')
    sys.modules[module.__name__] = module
    exec(compile(ast.Module(body=nodes, type_ignores=[]), '<pinned-suite-claims>', 'exec'), module.__dict__)
    return module


def read_target(issue_number, pr_number):
    issue = get(f'{ROOT}/issues/{issue_number}')
    if 'pull_request' in issue:
        raise Unknown('target_must_be_issue')
    comments = pages(f'{ROOT}/issues/{issue_number}/comments')
    result = dict(issue=issue, comments=comments, pr=None, checks=[], statuses=[], reviews=[], pr_comments=[], unavailable=[])
    if pr_number:
        pr = get(f'{ROOT}/pulls/{pr_number}')
        if pr['base']['repo']['full_name'] != REPO:
            raise Unknown('foreign_pr')
        result['pr'] = pr
        sha = pr['head']['sha']
        if not re.fullmatch('[0-9a-f]{40}', sha):
            raise Unknown('invalid_head')
        try:
            result['checks'] = pages(f'{ROOT}/commits/{sha}/check-runs?filter=all', 'check_runs')
        except Unknown as exc:
            result['unavailable'].append(str(exc))
        try:
            result['statuses'] = pages(f'{ROOT}/commits/{sha}/statuses')
        except Unknown as exc:
            result['unavailable'].append(str(exc))
        result['reviews'] = pages(f'{ROOT}/pulls/{pr_number}/reviews')
        result['pr_comments'] = pages(f'{ROOT}/issues/{pr_number}/comments')
    return result


def collect(issue_number, pr_number):
    revision = get(f'{ROOT}/commits/main')['sha']
    sources = {}
    for path in PINS:
        value = get(f'{ROOT}/contents/{path}?ref={revision}')
        sources[path] = base64.b64decode(value['content'])
    claims = resolver(sources)
    first = read_target(issue_number, pr_number)
    second = read_target(issue_number, pr_number)
    if canonical(first) != canonical(second):
        raise Unknown('observation_changed_reread')
    if get(f'{ROOT}/commits/main')['sha'] != revision:
        raise Unknown('suite_main_changed_reread')
    return second, claims, revision


def project(snapshot, claims, now, revision):
    issue = snapshot['issue']
    comments = unique(snapshot['comments'])
    labels = sorted(label['name'] for label in issue['labels'])
    pr = snapshot['pr']
    active = claims.active_claims(comments, issue.get('body') or '', now=now)
    malformed = any('[WORK_CLAIM]' in row.get('body', '') and claims.parse_comment(row) is None
                    for row in comments)
    state = 'unknown'
    reason = 'bounded_evidence_does_not_establish_execution_authority'
    operation = None
    if snapshot.get('unavailable'):
        reason = 'incomplete_remote_evidence'
    elif malformed:
        reason = 'invalid_claim_evidence'
    elif any(label == 'state:blocked' or label == 'agent:blocked' or label.startswith('blocked:')
             or label == 'decision:owner-required' for label in labels):
        state, reason = 'blocked', 'suite_blocking_label'
    elif issue['state'] == 'closed':
        state, reason = 'terminal', 'issue_closed_no_new_operation'
    elif active:
        state, reason, operation = 'waiting', 'canonical_active_claim', 'wait_for_claim_holder'
    elif any(label in labels for label in ('agent:running', 'agent:dispatched')):
        reason = 'vendor_attempt_requires_queue_provenance_not_generic_claim'
    elif pr and pr['state'] == 'open':
        if pr['draft']:
            state, reason = 'waiting', 'draft_pr_not_reviewable'
        elif any(check['head_sha'] != pr['head']['sha'] for check in snapshot['checks']):
            reason = 'check_head_mismatch'
        elif any(check['status'] != 'completed' for check in snapshot['checks']) or any(
                status['state'] == 'pending' for status in snapshot['statuses']):
            state, reason, operation = 'qualifying', 'observed_checks_pending', 'wait_for_current_head_checks'
        else:
            reason = 'check_completion_does_not_establish_required_qualification_or_dev_pass'
    stable = dict(snapshot, comments=comments)
    for key in ('checks', 'statuses', 'reviews', 'pr_comments'):
        stable[key] = unique(stable[key])
    return dict(schema=1, repository=REPO, issue=issue['number'], suite_revision=revision,
                evidence_digest=digest(stable), labels=labels,
                pr=None if not pr else dict(number=pr['number'], state=pr['state'],
                    head=pr['head']['sha'], base=pr['base']['sha'], draft=pr['draft']),
                active_claims=[dict(key=c.claim_key, worker=c.worker_class, scope=c.scope,
                    acquire_comment_id=c.acquire_comment_id, lease_until=claims.format_time(c.lease_until))
                    for c in active],
                unavailable=sorted(snapshot.get('unavailable', [])),
                check_count=len(stable['checks']), status_count=len(stable['statuses']),
                review_count=len(stable['reviews']), state=state, reason=reason,
                next_permitted_operation=operation, mutation_authorized=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--issue', type=int, required=True)
    parser.add_argument('--pr', type=int)
    args = parser.parse_args()
    try:
        if args.issue <= 0 or (args.pr is not None and args.pr <= 0):
            raise Unknown('invalid_target')
        snapshot, claims, revision = collect(args.issue, args.pr)
        value = project(snapshot, claims, dt.datetime.now(dt.timezone.utc), revision)
    except (Unknown, KeyError, ValueError, TypeError, OSError, subprocess.TimeoutExpired) as exc:
        value = dict(schema=1, state='unknown', reason=str(exc) if isinstance(exc, Unknown)
                     else 'incomplete_or_invalid_evidence', next_permitted_operation=None,
                     mutation_authorized=False)
    print(json.dumps(value, sort_keys=True, indent=2))
    return 2 if value['state'] == 'unknown' else 0


if __name__ == '__main__':
    sys.exit(main())
