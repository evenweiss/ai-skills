"""Run the installed Codex plugin against a local model and desktop fixture."""
import json
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
from threading import Thread

from check_reports import audit
from desktop_fixture import (BINARY, CREATE, FORK, HANDOFF, MARKER, MOCK_COORDINATOR, MOCK_TARGET, TOOL,
                             MockDesktop, ModelFixture, developer_context, new_thread,
                             process_app, setup, trust_fixture_hooks, turn)

READ = 'read_thread'


def command(script, cwd):
    return ('exec_command', {'cmd': script, 'workdir': str(cwd), 'login': False})


def packet(data):
    return 'Fixture task and responsibility.\n\n```workflow-dispatch\n' + json.dumps(data) + '\n```'


def install(marketplace, root, env):
    catalog = json.loads((marketplace / '.agents/plugins/marketplace.json').read_text())
    plugin_id = f"ai-development-workflow@{catalog['name']}"
    for args in (['marketplace', 'add', str(marketplace), '--json'], ['add', plugin_id, '--json']):
        result = subprocess.run([str(BINARY), 'plugin', *args], env=env, cwd=root,
                                capture_output=True, text=True, timeout=20)
        assert result.returncode == 0, result.stderr
    return Path(json.loads(result.stdout)['installedPath'])


def check_protected_handoff(rpc, model, desktop, old_registration, policy, sample, coordination, source):
    old = policy['coordinator']
    candidate_state = new_thread(rpc, coordination.parent, ':read-only')
    assert candidate_state['activePermissionProfile']['id'] == ':read-only', candidate_state
    candidate = candidate_state['thread']['id']
    desktop.handoff_candidate = candidate
    target = {'target': {'type': 'projectless'}}
    candidate_address = {'threadId': candidate, 'hostId': 'local'}
    executor_address = {'threadId': MOCK_TARGET}
    candidate_registration = old_registration.with_name(candidate + '.json')
    task = {key: sample[key] for key in ('task', 'version')}
    candidate_reporting = {**sample['reporting'], 'recipient': old,
                           'deliverable': 'first-turn read evidence and findings'}
    verify_route = {'role': '候选统筹', 'reporting': candidate_reporting,
                    'checkpoint': sample['checkpoint']}
    followup = packet({**task, **verify_route})
    create_prompt = f"只读读取任务 {task['task']} 的权威记录 {coordination}。\n\n" + followup
    ordinary = packet(sample)

    def dispatch(sender, tool, address, prompt, allowed):
        count = len(desktop.calls)
        response = turn(rpc, model, sender, 'protected handoff fixture',
                        (tool, {**address, 'prompt': prompt}))
        assert len(desktop.calls) == count + int(allowed), desktop.calls[count:]
        if not allowed:
            assert '派单校验未通过' in json.dumps(response, ensure_ascii=False), response
        return response

    try:
        # The isolated desktop uses this already provisioned thread as the create receipt.
        candidate_registration.write_text(json.dumps({**task, 'coordinator': candidate, 'routes': []}))
        scoped = {**policy, 'routes': [{**verify_route, **target}]}
        old_registration.write_text(json.dumps(scoped))
        created = dispatch(old, CREATE, target, create_prompt, True)
        assert candidate in json.dumps(created), created
        assert desktop.calls[-1] == (CREATE, {**target, 'prompt': create_prompt})
        dispatch(old, TOOL, candidate_address, followup, False)
        scoped['routes'].append({**verify_route, **candidate_address})
        old_registration.write_text(json.dumps(scoped))
        dispatch(old, TOOL, candidate_address, followup, True)
        dispatch(old, TOOL, {'threadId': candidate}, followup, False)
        dispatch(old, TOOL, candidate_address, ordinary, False)
        active = {**candidate_reporting, 'mode': 'active', 'authorization': 'approved',
                  'source': 'fixture approval'}
        scoped['routes'][-1]['reporting'] = active
        old_registration.write_text(json.dumps(scoped))
        dispatch(old, TOOL, candidate_address, packet({**task, **verify_route, 'reporting': active}), False)

        before = coordination.read_bytes()
        read = turn(rpc, model, candidate, 'first-turn record verification',
                    command('/bin/cat ' + shlex.quote(str(coordination)), coordination.parent))
        assert before.decode().strip() in json.dumps(read, ensure_ascii=False), read
        write = turn(rpc, model, candidate, 'candidate must stay read-only',
                     command('printf forbidden > ' + shlex.quote(str(coordination)), coordination.parent))
        assert coordination.read_bytes() == before, write
        dispatch(candidate, TOOL, executor_address, ordinary, False)
        dispatch(candidate, CREATE, target, ordinary, False)
        dispatch(candidate, FORK, executor_address, '', False)
        dispatch(candidate, HANDOFF, executor_address, '', False)

        # The fixture operator serializes the handoff and grants dispatch only after cutover.
        old_registration.write_text(json.dumps({**policy, 'routes': []}))
        dispatch(old, TOOL, executor_address, ordinary, False)
        dispatch(candidate, TOOL, executor_address, ordinary, False)
        cutover = coordination.parent / 'cutover.json'
        committed = {'task': task['task'], 'from': old, 'coordinator': candidate, 'effective': 'fixture-cutover'}
        cutover.write_text(json.dumps(committed))
        received = turn(rpc, model, candidate, 'confirm cutover from recorded evidence',
                        command('/bin/cat ' + shlex.quote(str(cutover)), coordination.parent))
        assert json.dumps(committed) in str(received), received
        dispatch(candidate, TOOL, executor_address, ordinary, False)
        executor_route = {key: sample[key] for key in ('role', 'reporting', 'checkpoint')}
        candidate_registration.write_text(json.dumps({**task, 'coordinator': candidate,
                                                     'routes': [{**executor_route, **executor_address}]}))
        dispatch(old, TOOL, executor_address, ordinary, False)
        dispatch(candidate, TOOL, executor_address, 'missing packet after cutover', False)
        dispatch(candidate, TOOL, executor_address, ordinary, True)
        after = turn(rpc, model, candidate, 'successor keeps business read-only',
                     command('printf forbidden > ' + shlex.quote(str(source)), source.parent))
        assert source.read_text() == 'fixture baseline\n', after
        print('PASS protected handoff: candidate creation and recheck, read-only first turn, guarded cutover', flush=True)
    finally:
        desktop.handoff_candidate = None
        old_registration.write_text(json.dumps(policy))
        candidate_registration.unlink(missing_ok=True)


def run(root, marketplace, model, desktop, socket_path):
    business, records = root/'business', root/'records'
    business.mkdir()
    records.mkdir()
    source = business/'app.txt'
    source.write_text('fixture baseline\n')
    coordination = records/'coordination.md'
    coordination.write_text('WF-42 coordinator fixture\n')
    env, cfg = setup(root, model, socket_path, 'default_permissions = ":workspace"')
    with cfg.open('a') as f:
        f.write(f'''
[permissions.workflow-coordinator.filesystem]
":root" = "read"
{json.dumps(str(records))} = "write"
''')
    script = install(marketplace, root, env)/'skills/ai-development-workflow/scripts/codex_compact.py'
    trust_fixture_hooks(root, env, cfg, business)
    task = {'task': 'WF-42', 'version': 'v2'}
    checkpoint = {'owner': 'fixture-R', 'trigger': 'manual fixture at 15:00', 'entry': 'read_thread'}
    reporting = {'events': ['completed', 'stopped', 'blocked'], 'recipient': 'fixture-C',
                 'entry': 'read_thread', 'deliverable': 'candidate and evidence',
                 'mode': 'read-only', 'authorization': 'pending'}
    role = '开发执行者'
    route = {'role': role, 'reporting': reporting, 'checkpoint': checkpoint}
    policy = {**task, 'routes': [{**route, 'threadId': MOCK_TARGET},
                                {**route, 'target': {'type': 'projectless'}}]}
    sample = {**task, **route}
    with process_app(root, env) as rpc:
        hooks = rpc.call('hooks/list', {'cwds': [str(business)]})['data'][0]['hooks']
        assert len(hooks) == 2 and all(h['trustStatus'] == 'trusted' for h in hooks), hooks
        state = new_thread(rpc, business, 'workflow-coordinator')
        assert state['activePermissionProfile']['id'] == 'workflow-coordinator', state['activePermissionProfile']
        coordinator = state['thread']['id']
        policy['coordinator'] = coordinator
        path = cfg.parent/'ai-development-workflow'/'dispatch'/(coordinator+'.json')
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps(policy))
        subprocess.run(['/usr/bin/python3', '-B', str(script), 'register', coordinator, task['task'], str(coordination)],
                       env=env, check=True, timeout=5)
        assert not any(MARKER in developer_context(body)
                       for body in turn(rpc, model, coordinator, 'before compaction'))
        model.use()
        rpc.call('thread/compact/start', {'threadId': coordinator})
        rpc.finish_turn(coordinator)
        after = turn(rpc, model, coordinator, 'after compaction', command("printf forbidden > app.txt", business))
        if not any(MARKER in developer_context(body) and str(coordination) in developer_context(body) for body in after):
            print(json.dumps(rpc.call('hooks/list', {'cwds': [str(business)]}), ensure_ascii=False))
            for event in rpc.events:
                if 'hook' in event.get('method','').lower():
                    print(json.dumps(event, ensure_ascii=False))
            raise AssertionError('missing compaction context')
        assert source.read_text() == 'fixture baseline\n'
        assert any(reason in json.dumps(after).lower() for reason in ('operation not permitted', 'permission denied', 'read-only'))
        python_write = '/usr/bin/python3 -B -c ' + shlex.quote("from pathlib import Path; Path('app.txt').write_text('forbidden')")
        alternate = turn(rpc, model, coordinator, 'direct file write', command(python_write, business))
        assert 'PermissionError' in json.dumps(alternate) and source.read_text() == 'fixture baseline\n'
        approval_write = command('printf nope > ' + shlex.quote(str(path)), business)
        before_policy = path.read_bytes()
        turn(rpc, model, coordinator, 'try rewriting registration', approval_write)
        assert path.read_bytes() == before_policy
        note = records/'note.txt'
        turn(rpc, model, coordinator, 'write coordination', command('printf allowed > ' + shlex.quote(str(note)), business))
        assert note.read_text() == 'allowed'
        print('PASS compaction: reminder recovered; business and policy writes denied; coordination write allowed', flush=True)

        def send(tool, dest, prompt, allowed):
            before = len(desktop.calls)
            result = turn(rpc, model, coordinator, 'outgoing dispatch scenario', (tool, {**dest, 'prompt': prompt}))
            assert len(desktop.calls) == before + int(allowed), (tool, desktop.calls)
            if not allowed:
                assert '派单校验未通过' in json.dumps(result, ensure_ascii=False)

        for tool, dest in ((TOOL, {'threadId': MOCK_TARGET}), (CREATE, {'target': {'type': 'projectless'}})):
            send(tool, dest, 'fixture without reporting', False)
            send(tool, dest, packet({**sample, 'reporting': {}}), False)
            send(tool, dest, packet(sample), True)
        send(TOOL, {'threadId': MOCK_COORDINATOR}, packet(sample), False)
        send(TOOL, {'threadId': MOCK_TARGET, 'hostId': 'local'}, packet(sample), False)
        send(TOOL, {'threadId': MOCK_TARGET}, packet({**sample, 'version': 'v1'}), False)
        send(TOOL, {'threadId': MOCK_TARGET}, packet({**sample, 'checkpoint': {**checkpoint, 'trigger': 'executor self report'}}), False)
        for tool in (FORK, HANDOFF):
            before = len(desktop.calls)
            result = turn(rpc, model, coordinator, 'alternate dispatch', (tool, {'threadId': MOCK_TARGET}))
            assert len(desktop.calls) == before and '派单校验未通过' in json.dumps(result, ensure_ascii=False)
        active = {**reporting, 'mode': 'active', 'authorization': 'approved', 'entry': 'fixture send',
                  'source': 'fixture user approval'}
        active_destination = {'threadId': MOCK_TARGET, 'hostId': 'local'}
        policy['routes'][0] = {**route, **active_destination, 'reporting': active}
        path.write_text(json.dumps(policy))
        missing_source = {key: value for key, value in active.items() if key != 'source'}
        send(TOOL, active_destination, packet({**sample, 'reporting': missing_source}), False)
        send(TOOL, active_destination, packet({**sample, 'reporting': active}), True)
        path.write_text('{bad json')
        send(TOOL, {'threadId': MOCK_TARGET}, packet(sample), False)
        path.write_text(json.dumps(policy))
        print('PASS dispatch: installed Hook blocks incomplete packets and unregistered routes before delivery', flush=True)

        check_protected_handoff(rpc, model, desktop, path, policy, sample, coordination, source)

        desktop.reports = {
            MOCK_TARGET: {**task, 'status': 'completed', 'outboundReceipt': 'not_sent', 'artifact': 'candidate.json'},
            MOCK_COORDINATOR: {**task, 'collection': 'not_collected', 'userNotice': 'not_sent', 'acceptance': 'pending'},
        }
        artifact = business/'candidate.json'
        artifact.write_text(json.dumps({**task, 'result': 'isolation candidate'}))
        monitor = new_thread(rpc, business, ':read-only')['thread']['id']
        before = len(desktop.calls)
        messages = turn(rpc, model, monitor, 'manual independent checkpoint',
                        (READ, {'threadId': MOCK_COORDINATOR}), (READ, {'threadId': MOCK_TARGET}),
                        command('/bin/cat ' + shlex.quote(str(artifact)), business))
        assert [name for name,_ in desktop.calls[before:]] == [READ, READ]
        assert all(value in json.dumps(messages) for value in ('not_collected', 'not_sent', 'isolation candidate'))
        check = {**task, 'due': True, 'closed': False, 'userNotificationApproved': True, 'coordinator': 'fixture-C'}
        outcome = audit(check, desktop.reports[MOCK_COORDINATOR], desktop.reports[MOCK_TARGET], artifact)
        assert outcome['status'] == 'candidate_available'
        assert not outcome['executorDelivered'] and not outcome['coordinatorCollected']
        assert outcome['coordinatorMissedNotice'] and outcome['independentAcceptance'] == 'pending'
        assert outcome['notification'] == 'draft_for_authorized_user_route' and outcome['nextOwner'] == 'fixture-C'
        assert audit({**check, 'closed': True}, desktop.reports[MOCK_COORDINATOR],
                     desktop.reports[MOCK_TARGET], artifact)['notification'] == 'none'
        assert audit({**check, 'userNotificationApproved': False}, desktop.reports[MOCK_COORDINATOR],
                     desktop.reports[MOCK_TARGET], artifact)['notification'] == 'awaiting_authorization'
        assert audit(check, desktop.reports[MOCK_COORDINATOR],
                     {**desktop.reports[MOCK_TARGET], 'version': 'v1'}, artifact)['status'] == 'stale_or_unverified'
        print('PASS silent parties: independent check reads candidate and drafts notification, without sending', flush=True)

        ordinary_state = new_thread(rpc, business)
        assert ordinary_state['activePermissionProfile']['id'] == ':workspace'
        ordinary = ordinary_state['thread']['id']
        before = len(desktop.calls)
        turn(rpc, model, ordinary, 'ordinary development',
             command('printf ordinary > app.txt', business),
             (TOOL, {'threadId': MOCK_TARGET, 'prompt': 'ordinary message without task packet'}))
        assert source.read_text() == 'ordinary' and len(desktop.calls) == before + 1
        model.use()
        rpc.call('thread/compact/start', {'threadId': ordinary})
        rpc.finish_turn(ordinary)
        assert not any(MARKER in developer_context(body)
                       for body in turn(rpc, model, ordinary, 'ordinary after compaction'))
        path.unlink()
        send(TOOL, {'threadId': MOCK_TARGET}, 'registration removed', True)
        subprocess.run(['/usr/bin/python3', '-B', str(script), 'unregister', coordinator, task['task']],
                       env=env, check=True, timeout=5)
        model.use()
        rpc.call('thread/compact/start', {'threadId': coordinator})
        rpc.finish_turn(coordinator)
        assert not any(MARKER in developer_context(body)
                       for body in turn(rpc, model, coordinator, 'coordinator after unregister'))
        print('PASS scope: ordinary chat unaffected; unregister ends dispatch checks and compaction reminders', flush=True)

    with process_app(root, env, code_mode=True) as rpc:
        state = new_thread(rpc, business, 'workflow-coordinator')
        assert state['activePermissionProfile']['id'] == 'workflow-coordinator', state
        coordinator = state['thread']['id']
        registration = path.with_name(coordinator + '.json')
        registration.write_text(json.dumps({**task, 'coordinator': coordinator,
                                            'routes': [{**route, 'threadId': MOCK_TARGET}]}))
        incomplete = {key: value for key, value in sample.items() if key != 'reporting'}
        for data, allowed in ((sample, True), (incomplete, False)):
            arguments = {'threadId': MOCK_TARGET, 'prompt': packet(data)}
            script_input = f'text(await tools.mcp__codex_app__send_message_to_thread({json.dumps(arguments)}))'
            before = len(desktop.calls)
            replies = turn(rpc, model, coordinator, 'nested code-mode dispatch', ('exec', script_input))
            assert desktop.calls[before:] == ([(TOOL, arguments)] if allowed else []), desktop.calls[before:]
            outputs = [item for item in replies[-1]['input'] if item['type'] == 'custom_tool_call_output']
            expected = 'NO_REAL_DISPATCH' if allowed else '派单校验未通过'
            assert outputs and expected in json.dumps(outputs[-1], ensure_ascii=False), outputs
        print('PASS code mode: one valid nested dispatch delivered, incomplete dispatch denied before delivery', flush=True)


def main():
    marketplace = (Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[2]).resolve()
    with tempfile.TemporaryDirectory(prefix='workflow-test-', dir='/private/tmp') as temp:
        root = Path(temp)
        socket_path = root/'mock.sock'
        with ModelFixture() as model, MockDesktop(socket_path) as desktop:
            for server in (model, desktop):
                Thread(target=server.serve_forever, daemon=True).start()
            try:
                run(root, marketplace, model, desktop, socket_path)
            except Exception:
                log = root/'runtime.log'
                if log.is_file():
                    print(log.read_text()[-6500:], file=sys.stderr)
                raise
            finally:
                for server in (model, desktop):
                    server.shutdown()


if __name__ == '__main__':
    main()
