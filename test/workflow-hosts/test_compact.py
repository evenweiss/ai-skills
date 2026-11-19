import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

PLUGIN = Path(__file__).resolve().parents[2] / 'plugins' / 'ai-development-workflow'
SCRIPT = PLUGIN / 'skills' / 'ai-development-workflow' / 'scripts' / 'codex_compact.py'


class HostCompactionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.record = self.root / 'coordination record.md'
        self.record.write_text('protected coordination notes', encoding='utf-8')

    def call(self, host, args=(), event=None, config=None):
        return subprocess.run(
            [sys.executable, '-B', str(SCRIPT), '--host', host, '--config-dir',
             str(config or self.root / host), *args],
            input=json.dumps(event) if event else '',
            encoding='utf-8', capture_output=True, check=True, timeout=5,
        ).stdout

    def test_existing_session_start_contract(self):
        for host in ('codex', 'claude-code'):
            with self.subTest(host=host):
                self.call(host, ('register', 'S1', 'T1', str(self.record)))
                hook = {'hook_event_name': 'SessionStart', 'session_id': 'S1', 'source': 'compact'}
                output = json.loads(self.call(host, event=hook))['hookSpecificOutput']
                self.assertEqual(output['hookEventName'], 'SessionStart')
                self.assertIn(str(self.record), output['additionalContext'])
                self.assertNotIn('protected coordination notes', output['additionalContext'])
                self.assertEqual(self.call(host, event={**hook, 'source': 'startup'}), '')
                self.assertEqual(self.call(host, event={**hook, 'session_id': 'S2'}), '')
                self.call(host, ('unregister', 'S1', 'T1'))
                self.assertEqual(self.call(host, event=hook), '')

    def test_cursor_sends_only_pre_compaction_user_notice(self):
        hook = {'hook_event_name': 'preCompact', 'conversation_id': 'current-session'}
        self.call('cursor', ('register', 'current-session', 'CURSOR-TASK', str(self.record)))
        output = json.loads(self.call('cursor', event=hook))
        self.assertEqual(set(output), {'user_message'})
        self.assertIn('即将压缩', output['user_message'])
        self.assertIn(str(self.record), output['user_message'])
        self.assertNotIn('上下文刚压缩', output['user_message'])
        self.assertEqual(self.call('cursor', event={**hook, 'conversation_id': 'new-fork'}), '')
        self.assertEqual(self.call('cursor', event={**hook, 'hook_event_name': 'sessionStart'}), '')
        self.call('cursor', ('unregister', 'current-session', 'CURSOR-TASK'))
        self.assertEqual(self.call('cursor', event=hook), '')

    def test_context_uses_explicit_host_profile_and_opaque_id(self):
        session = 'Opaque id: here/only'
        self.call('pi', ('register', session, 'PI-TASK', str(self.record)))
        self.assertIn('PI-TASK', self.call('pi', ('context', session)))
        self.assertEqual(self.call('pi', ('context', session), config=self.root / 'other-profile'), '')
        self.assertEqual(self.call('hermes', ('context', session)), '')
        self.record.unlink()
        self.assertIn('不可读取', self.call('pi', ('context', session)))
        self.call('pi', ('unregister', session, 'PI-TASK'))
        self.assertEqual(self.call('pi', ('context', session)), '')


if __name__ == '__main__':
    unittest.main()
