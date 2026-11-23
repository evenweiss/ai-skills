"""Maintain task locators and restore coordination context after context compaction."""
import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import sys
import tempfile

SKILL = Path(__file__).resolve().parents[1] / 'SKILL.md'
HOST_CONFIG = {
    'codex': ('CODEX_HOME', '.codex'),
    'claude-code': ('CLAUDE_CONFIG_DIR', '.claude'),
    'cursor': (None, '.cursor'),
    'pi': ('PI_CODING_AGENT_DIR', '.pi/agent'),
    'hermes': ('HERMES_HOME', '.hermes'),
}


def identifier(value):
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}', value):
        raise argparse.ArgumentTypeError('Use an ID of 1–128 letters, digits, or _ . : -')
    return value


def session_identifier(host, value):
    if host in ('codex', 'claude-code'):
        return identifier(value)
    # Hosts can supply opaque IDs. Only their hashes are used as path components.
    if not isinstance(value, str) or not value or not value.isprintable() or len(value.encode()) > 4096:
        raise argparse.ArgumentTypeError('Use a valid host session ID.')
    return value


def session_dir(host, session, config_dir=None):
    config_var, default = HOST_CONFIG[host]
    configured = os.environ.get(config_var) if config_var else None
    base = Path(config_dir or configured or Path.home() / default).expanduser()
    session_hash = sha256(session_identifier(host, session).encode()).hexdigest()
    return base / 'ai-development-workflow' / 'coordinators' / session_hash


def readable_record(path):
    return path.is_absolute() and path.is_file() and os.access(path, os.R_OK)


def registration_path(host, session, task, config_dir=None):
    return session_dir(host, session, config_dir) / (sha256(identifier(task).encode()).hexdigest() + '.json')


def unregister_task(host, session, task, config_dir=None):
    registration_path(host, session, task, config_dir).unlink(missing_ok=True)


def register_task(host, session, task, record, config_dir=None):
    entry = registration_path(host, session, task, config_dir)
    record = Path(record)
    if not readable_record(record):
        raise ValueError('Provide an absolute path to a readable coordination record.')
    directory = entry.parent
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    # Each task has its own file, so an update never rewrites other registrations.
    with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=directory, delete=False) as file:
        pending = Path(file.name)
        try:
            json.dump({'task': task, 'record': str(record)}, file, ensure_ascii=False)
            file.close()
            pending.replace(entry)
        finally:
            pending.unlink(missing_ok=True)


def registration_context(host, session, config_dir=None, *, before_compaction=False):
    def quote(value):
        return json.dumps(str(value), ensure_ascii=False)

    tasks = []
    invalid_entries = 0
    for entry in sorted(session_dir(host, session, config_dir).glob('*.json')):
        try:
            info = json.loads(entry.read_text(encoding='utf-8'))
            task = identifier(info['task'])
            record = Path(info['record'])
            if host == 'codex' and not record.is_absolute():
                raise ValueError('Expected an absolute record path.')
            readable = readable_record(record)
        except FileNotFoundError:
            # An entry can be unregistered after the directory listing.
            continue
        except (ValueError, OSError, TypeError, KeyError, argparse.ArgumentTypeError):
            invalid_entries += 1
            continue
        locator = f'- 任务 {quote(task)}，协调记录 {quote(record)}'
        if not readable:
            locator += '（不可读取。先做只读核查，暂缓受影响的写入或实质验证。）'
        tasks.append(locator)
    diagnostics = []
    if host == 'codex' and invalid_entries:
        diagnostics.append(f'本会话有 {invalid_entries} 份续接登记无法读取或格式无效。请由获授权的配置者核对登记。')
    if not tasks:
        return '\n'.join(diagnostics)
    notice = (
        '即将压缩。压缩后请手动按以下入口恢复已登记的统筹任务。'
        if before_compaction else
        '上下文刚压缩。这条提醒仅适用于下列任务。登记只是查找记录的入口。'
    )
    return '\n'.join([
        notice,
        f'重新读取技能 {quote(SKILL)} 和适用引用。处理下列任务时，逐项核对最新分工、执行者和授权。',
        '确认在该任务仍为统筹时，沿用分工，复用有效派单或按已有授权下发，由执行者实施。',
        '若角色或写入归属未核实，先做只读核查，暂缓该任务受影响的写入或实质验证。',
        '其他任务仍按各自的分工处理。',
        *tasks,
        *diagnostics,
    ])


def run_hook(host, config_dir=None):
    event = json.load(sys.stdin)
    if host == 'cursor':
        if event.get('hook_event_name') != 'preCompact':
            return
        session = event.get('conversation_id')
        if not session:
            return
        context = registration_context(host, session, config_dir, before_compaction=True)
        if context:
            print(json.dumps({'user_message': context}, ensure_ascii=False))
        return
    if host not in ('codex', 'claude-code'):
        return
    if event.get('hook_event_name') != 'SessionStart' or event.get('source') != 'compact':
        return
    context = registration_context(host, event['session_id'], config_dir)
    if context:
        print(json.dumps({'hookSpecificOutput': {
            'hookEventName': 'SessionStart', 'additionalContext': context,
        }}, ensure_ascii=False))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host', choices=HOST_CONFIG, default='codex')
    parser.add_argument('--config-dir', type=Path)
    actions = parser.add_subparsers(dest='action')
    for action in ('register', 'unregister', 'context'):
        command = actions.add_parser(action)
        command.add_argument('session')
        if action in ('register', 'unregister'):
            command.add_argument('task', type=identifier)
        if action == 'register':
            command.add_argument('record', type=Path)
    args = parser.parse_args()
    try:
        if args.action == 'register':
            register_task(args.host, args.session, args.task, args.record, args.config_dir)
        elif args.action == 'unregister':
            unregister_task(args.host, args.session, args.task, args.config_dir)
        elif args.action == 'context':
            context = registration_context(args.host, args.session, args.config_dir)
            if context:
                print(context)
        else:
            run_hook(args.host, args.config_dir)
    except (OSError, ValueError, argparse.ArgumentTypeError) as error:
        parser.exit(1, f'{error}\n')


if __name__ == '__main__':
    main()
