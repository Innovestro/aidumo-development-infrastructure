import copy
import datetime as dt
import os
from pathlib import Path
import unittest
from unittest.mock import patch

import shadow


class ShadowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root = Path(os.environ['SUITE_CHECKOUT'])
        cls.sources = {p: (root / p).read_bytes() for p in shadow.PINS}
        cls.claims = shadow.resolver(cls.sources)

    def setUp(self):
        self.now = dt.datetime(2026, 9, 28, 20, tzinfo=dt.timezone.utc)
        self.data = dict(issue=dict(number=42, state='open', body='', labels=[]),
                         comments=[], pr=None, checks=[], statuses=[], reviews=[], pr_comments=[])

    def project(self):
        return shadow.project(self.data, self.claims, self.now, 'a' * 40)

    def claim(self, number=1, event='acquire'):
        return dict(id=number, created_at='2026-09-28T19:50:00Z',
                    body='[WORK_CLAIM]\nClaim-Format-Version: 3\nEvent: ' + event +
                    '\nClaim-Key: test\nWorker-Class: DEV\nScope: exclusive\n'
                    'Worker-Context-UID: DEV-I-260928195000-abcd\nLease-Until: 2026-09-28T21:00:00Z')

    def pr(self):
        self.data['pr'] = dict(number=43, state='open', head=dict(sha='b'*40),
                               base=dict(sha='c'*40), draft=False)

    def test_restart_no_local_state(self):
        self.data['comments'] = [self.claim()]
        first = self.project()
        fresh = shadow.resolver(self.sources)
        self.assertEqual(first, shadow.project(copy.deepcopy(self.data), fresh, self.now, 'a'*40))
        self.assertEqual(first['next_permitted_operation'], 'wait_for_claim_holder')

    def test_duplicate_and_out_of_order(self):
        self.data['comments'] = [self.claim(), self.claim(2, 'complete')]
        expected = self.project()
        self.data['comments'] = [self.claim(2, 'complete'), self.claim(), self.claim()]
        self.assertEqual(expected, self.project())
        self.assertEqual(expected['active_claims'], [])

    def test_conflicting_duplicate_fails(self):
        self.data['comments'] = [self.claim(), self.claim(1, 'complete')]
        with self.assertRaises(shadow.Unknown):
            self.project()

    def test_missing_authority(self):
        self.assertEqual(self.project()['state'], 'unknown')
        self.assertIsNone(self.project()['next_permitted_operation'])

    def test_invalid_claim(self):
        self.data['comments'] = [dict(id=1, body='[WORK_CLAIM]\nEvent: nonsense')]
        self.assertEqual(self.project()['reason'], 'invalid_claim_evidence')

    def test_expired_claim_is_not_resurrected(self):
        self.data['comments'] = [self.claim()]
        self.now += dt.timedelta(hours=2)
        self.assertEqual(self.project()['active_claims'], [])

    def test_blocker_overrides_claim(self):
        self.data['comments'] = [self.claim()]
        self.data['issue']['labels'] = [dict(name='decision:owner-required')]
        self.assertEqual(self.project()['state'], 'blocked')
        self.assertIsNone(self.project()['next_permitted_operation'])

    def test_changed_head_and_base(self):
        self.pr()
        initial = self.project()
        self.data['pr']['head']['sha'] = 'd'*40
        head = self.project()
        self.data['pr']['base']['sha'] = 'e'*40
        self.assertNotEqual(initial['evidence_digest'], head['evidence_digest'])
        self.assertNotEqual(head['evidence_digest'], self.project()['evidence_digest'])

    def test_current_pending_checks(self):
        self.pr()
        self.data['checks'] = [dict(id=1, head_sha='b'*40, status='in_progress')]
        self.assertEqual(self.project()['next_permitted_operation'], 'wait_for_current_head_checks')
        self.data['checks'][0]['head_sha'] = 'd'*40
        self.assertEqual(self.project()['state'], 'unknown')

    def test_green_is_not_pass(self):
        self.pr()
        self.data['checks'] = [dict(id=1, head_sha='b'*40, status='completed', conclusion='success')]
        self.assertEqual(self.project()['state'], 'unknown')
        self.assertFalse(self.project()['mutation_authorized'])

    def test_vendor_claim_not_inferred(self):
        self.data['issue']['labels'] = [dict(name='agent:running')]
        self.assertEqual(self.project()['state'], 'unknown')

    def test_unreadable_checks_retain_target_but_block_operation(self):
        self.pr()
        self.data['comments'] = [self.claim()]
        self.data['unavailable'] = ['read_unavailable:checks']
        value = self.project()
        self.assertEqual(value['state'], 'unknown')
        self.assertEqual(value['pr']['head'], 'b'*40)
        self.assertEqual(len(value['active_claims']), 1)
        self.assertIsNone(value['next_permitted_operation'])

    def test_contract_drift(self):
        sources = dict(self.sources)
        sources['.github/scripts/work_claim.py'] += b'\n'
        with self.assertRaises(shadow.Unknown):
            shadow.resolver(sources)

    def test_no_suite_writers_loaded(self):
        for name in ('GitHub', 'acquire', 'heartbeat', 'release', 'main', 'urllib', 'os', 'subprocess'):
            self.assertFalse(hasattr(self.claims, name), name)

    def test_transport_only_get(self):
        with patch.object(shadow.subprocess, 'run') as run:
            run.return_value.returncode = 0
            run.return_value.stdout = '{}'
            shadow.get(shadow.ROOT + '/issues/42')
            self.assertEqual(run.call_args.args[0], ['gh', 'api', '--method', 'GET', shadow.ROOT + '/issues/42'])
        with self.assertRaises(shadow.Unknown):
            shadow.get('https://example.com')

    def test_read_failure_is_unknown(self):
        with patch.object(shadow.subprocess, 'run') as run:
            run.return_value.returncode = 1
            with self.assertRaises(shadow.Unknown):
                shadow.get(shadow.ROOT + '/issues/42')

    def test_pagination_and_duplicate(self):
        page = [dict(id=i) for i in range(100)]
        with patch.object(shadow, 'get', side_effect=[page, [dict(id=99), dict(id=100)]]):
            self.assertEqual(len(shadow.pages(shadow.ROOT + '/issues/42/comments')), 101)

    def test_mutation_during_read(self):
        changed = copy.deepcopy(self.data)
        changed['issue']['state'] = 'closed'
        values = [dict(sha='a'*40)]
        import base64
        values += [dict(content=base64.b64encode(self.sources[p]).decode()) for p in shadow.PINS]
        with patch.object(shadow, 'get', side_effect=values), patch.object(
                shadow, 'read_target', side_effect=[self.data, changed]):
            with self.assertRaisesRegex(shadow.Unknown, 'observation_changed'):
                shadow.collect(42, None)


if __name__ == '__main__':
    unittest.main()
