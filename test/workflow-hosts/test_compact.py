from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import shutil
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

    def call(self, host, args=(), event=None, config=None, script=SCRIPT):
        return subprocess.run(
            [sys.executable, '-B', str(script), '--host', host, '--config-dir',
             str(config or self.root / host), *args],
            input=json.dumps(event) if event else '',
            encoding='utf-8', capture_output=True, check=True, timeout=5,
        ).stdout

    def cursor_hook_copy(self, name):
        script = self.root / name / SCRIPT.relative_to(PLUGIN)
        script.parent.mkdir(parents=True)
        return shutil.copyfile(SCRIPT, script)

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

    def test_codex_reports_invalid_registrations_and_recovers_valid_tasks(self):
        event = {'hook_event_name': 'SessionStart', 'session_id': 'S1', 'source': 'compact'}
        profile = self.root / 'codex'
        self.assertEqual(self.call('codex', event=event), '')
        self.call('codex', ('register', 'S1', 'BAD', str(self.record)))
        entry, = profile.rglob('*.json')
        for invalid in ('private malformed entry', '{"task":"BAD","record":"private-relative-path"}'):
            with self.subTest(invalid=invalid):
                entry.write_text(invalid, encoding='utf-8')
                output = json.loads(self.call('codex', event=event))['hookSpecificOutput']
                self.assertEqual(output['hookEventName'], 'SessionStart')
                warning = output['additionalContext']
                self.assertIn('续接登记', warning)
                self.assertIn('配置者', warning)
                self.assertNotIn('private', warning)
                self.assertNotIn(str(self.record), warning)
                self.assertNotIn('BAD', warning)

        self.assertEqual(self.call('codex', event={**event, 'session_id': 'S2'}), '')
        entry.unlink()
        entry.mkdir()
        for host in ('pi', 'hermes'):
            self.assertEqual(self.call(host, ('context', 'S1'), config=profile), '')

        self.call('codex', ('register', 'S1', 'GOOD', str(self.record)))
        context = json.loads(self.call('codex', event=event))['hookSpecificOutput']['additionalContext']
        self.assertIn('续接登记', context)
        self.assertIn('GOOD', context)
        self.assertIn(str(self.record), context)
        self.assertNotIn('protected coordination notes', context)

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

    def test_cursor_deduplicates_concurrent_installations_per_compaction(self):
        hook = {'hook_event_name': 'preCompact', 'conversation_id': 'current-session',
                'generation_id': 'generation-1', 'trigger': 'manual', 'message_count': 12}
        self.call('cursor', ('register', hook['conversation_id'], 'CURSOR-TASK', str(self.record)))
        scripts = [self.cursor_hook_copy(name) for name in ('cursor-native', 'claude-imported')]
        next_compaction = {**hook, 'message_count': 8}
        next_generation = {**hook, 'generation_id': 'generation-2'}

        with ThreadPoolExecutor(max_workers=2) as pool:
            for event in (hook, next_compaction, next_compaction, next_generation):
                outputs = list(pool.map(lambda script: self.call('cursor', event=event, script=script), scripts))
                notices = [json.loads(output)['user_message'] for output in outputs if output]
                self.assertEqual(len(notices), 1, outputs)
                self.assertIn(str(self.record), notices[0])

        # Both the imported and native installation can be the first to run.
        for first, second in (scripts, scripts[::-1]):
            self.assertTrue(self.call('cursor', event=next_generation, script=first))
            self.assertEqual(self.call('cursor', event=next_generation, script=second), '')

    def test_cursor_single_installation_and_profile_isolation(self):
        event = {'hook_event_name': 'preCompact', 'conversation_id': 'current-session',
                 'generation_id': 'generation-1'}
        args = ('register', event['conversation_id'], 'CURSOR-TASK', str(self.record))
        self.call('cursor', args)
        self.assertTrue(self.call('cursor', event=event))
        self.assertTrue(self.call('cursor', event=event))

        imported = self.cursor_hook_copy('claude-imported')
        self.assertEqual(self.call('cursor', event=event, script=imported), '')
        profile = self.root / 'other-profile'
        self.call('cursor', args, config=profile)
        for _ in range(2):
            self.assertTrue(self.call('cursor', event=event, config=profile, script=imported))

        sibling = {**event, 'conversation_id': 'different-session'}
        self.call('cursor', ('register', sibling['conversation_id'], 'OTHER-TASK', str(self.record)))
        self.assertTrue(self.call('cursor', event=sibling, script=imported))
        self.assertEqual(self.call('cursor', event=sibling), '')

    def test_cursor_reminder_survives_missing_generation_and_unusable_state(self):
        event = {'hook_event_name': 'preCompact', 'conversation_id': 'current-session'}
        self.call('cursor', ('register', event['conversation_id'], 'CURSOR-TASK', str(self.record)))
        self.assertTrue(self.call('cursor', event=event))
        entry, = (self.root / 'cursor').rglob('*.json')
        (entry.parent / '.pre-compact-notice').mkdir()
        output = self.call('cursor', event={**event, 'generation_id': 'generation-1'})
        self.assertIn(str(self.record), json.loads(output)['user_message'])

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
