import unittest
from unittest.mock import patch

import publish

HEAD = 'a'*40
BRANCH = 'codex/17-test'


class FakeRemote:
    def __init__(self):
        self.branch = None
        self.rows = []
        self.pushes = 0
        self.creates = 0
        self.failure = None

    def head(self, branch):
        return self.branch

    def prs(self, branch):
        return self.rows

    def push_new(self, branch, head):
        self.pushes += 1
        if self.branch is not None:
            raise publish.Blocked('lease_rejected')
        self.branch = head
        if self.failure == 'push_response':
            raise publish.Blocked('lost_push_response')

    def create(self, branch, body, title):
        self.creates += 1
        if self.failure != 'create_absent':
            self.rows = [dict(number=18, html_url='https://github.com/' + publish.REPO + '/pull/18',
                head=dict(sha=HEAD, ref=BRANCH, repo=dict(full_name=publish.REPO)),
                base=dict(ref='main', repo=dict(full_name=publish.REPO)), body='Closes #17')]
        if self.failure in ('create_response', 'create_absent'):
            raise publish.Blocked('lost_create_response')


class PublisherTests(unittest.TestCase):
    def setUp(self):
        self.remote = FakeRemote()

    def run_publish(self):
        return publish.publish(self.remote, 17, BRANCH, HEAD, '/outside/body.md', 'Test')

    def test_success_duplicate_and_restart(self):
        first = self.run_publish()
        self.assertEqual(first, self.run_publish())
        self.assertEqual((self.remote.pushes, self.remote.creates), (1, 1))
        fresh = FakeRemote()
        fresh.branch, fresh.rows = self.remote.branch, self.remote.rows
        self.remote = fresh
        self.assertEqual(first, self.run_publish())
        self.assertEqual((fresh.pushes, fresh.creates), (0, 0))

    def test_lost_create_response_reconciles_once(self):
        self.remote.failure = 'create_response'
        self.assertEqual(self.run_publish()['result'], 'published')
        self.run_publish()
        self.assertEqual(self.remote.creates, 1)

    def test_ambiguous_absent_create_never_retries(self):
        self.remote.failure = 'create_absent'
        for _ in range(2):
            with self.assertRaises(publish.Blocked):
                self.run_publish()
        self.assertEqual(self.remote.creates, 1)

    def test_lost_push_response_never_creates(self):
        self.remote.failure = 'push_response'
        for _ in range(2):
            with self.assertRaises(publish.Blocked):
                self.run_publish()
        self.assertEqual((self.remote.pushes, self.remote.creates), (1, 0))

    def test_conflicting_branch_never_changes_it(self):
        self.remote.branch = 'b'*40
        with self.assertRaises(publish.Blocked):
            self.run_publish()
        self.assertEqual((self.remote.pushes, self.remote.creates), (0, 0))

    def test_multiple_or_conflicting_prs(self):
        self.run_publish()
        self.remote.rows *= 2
        with self.assertRaises(publish.Blocked):
            self.run_publish()
        self.remote.rows = self.remote.rows[:1]
        self.remote.rows[0]['body'] = 'Closes #99'
        with self.assertRaises(publish.Blocked):
            self.run_publish()
        self.assertEqual(self.remote.creates, 1)

    def test_closed_or_deleted_branch_pr_never_recreated(self):
        first = self.run_publish()
        self.remote.rows[0]['state'] = 'closed'
        self.remote.branch = None
        self.assertEqual(first, self.run_publish())
        self.assertEqual((self.remote.pushes, self.remote.creates), (1, 1))

    def test_concurrent_creator_fenced(self):
        original = self.remote.push_new
        def race(branch, head):
            self.remote.branch = head
            original(branch, head)
        self.remote.push_new = race
        with self.assertRaises(publish.Blocked):
            self.run_publish()
        self.assertEqual(self.remote.creates, 0)

    def test_push_uses_absent_ref_lease(self):
        with patch.object(publish, 'command') as command:
            publish.Remote().push_new(BRANCH, HEAD)
            self.assertEqual(command.call_args.args[0], ['git', 'push',
                '--force-with-lease=refs/heads/' + BRANCH + ':', 'origin', HEAD + ':refs/heads/' + BRANCH])


if __name__ == '__main__':
    unittest.main()
