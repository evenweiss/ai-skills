"""Hermes skill registration and coordinator reminders after compaction."""

from argparse import ArgumentTypeError
from contextlib import contextmanager
from importlib.util import module_from_spec, spec_from_file_location
import json
import logging
import os
from pathlib import Path
import shlex


HOST = "hermes"
PLUGIN = "ai-development-workflow"
SKILL = Path(__file__).resolve().parent / "skills" / PLUGIN / "SKILL.md"
HOOKS = {"post_compaction", "pre_llm_call"}
COMMAND = "workflow-coordinator"
USAGE = f"用法 /{COMMAND} register <任务ID> <协调记录绝对路径> 或 /{COMMAND} unregister <任务ID>"
MANUAL = "请从协调记录手动续接，核对最新分工、执行者和授权。"
LOGGER = logging.getLogger(__name__)


def _load_registration():
    script = SKILL.parent / "scripts" / "codex_compact.py"
    spec = spec_from_file_location("ai_development_workflow_registration", script)
    registration = module_from_spec(spec)
    spec.loader.exec_module(registration)
    return registration


@contextmanager
def _exclusive_lock(path):
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    # The lock is on a separate file because replacing the JSON changes its inode.
    with path.open("a+b") as lock:
        if os.name == "nt":
            import msvcrt

            lock.seek(0)
            msvcrt.locking(lock.fileno(), msvcrt.LK_LOCK, 1)
        else:
            import fcntl

            fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        yield


class _Recovery:
    def __init__(self, home):
        from hermes_state_ids import is_known_session_id
        from utils import atomic_json_write

        self.home = home
        self.registrations = _load_registration()
        self.state_path = home / PLUGIN / "hermes-recovery.json"
        self.write_json = atomic_json_write
        self.is_known_session_id = is_known_session_id

    def _native_id(self, value):
        if not isinstance(value, str) or not self.is_known_session_id(value):
            return False
        try:
            self.registrations.identifier(value)
        except (ArgumentTypeError, ValueError):
            return False
        return True

    @contextmanager
    def _locked_state(self):
        # The profile lock also covers changes to the task locators that redirects refer to.
        # An atomic update moves both the live binding and its pending reminder together.
        with _exclusive_lock(self.state_path.with_suffix(".lock")):
            try:
                state = json.loads(self.state_path.read_text(encoding="utf-8"))
            except FileNotFoundError:
                state = {}
            if not isinstance(state, dict):
                raise ValueError("Hermes 压缩续接状态格式无效。")
            yield state

    def _save(self, state):
        self.write_json(self.state_path, state, mode=0o600, fsync_dir=True)

    def _context(self, storage_session, *, before_compaction=False):
        return self.registrations.registration_context(
            HOST, storage_session, self.home, before_compaction=before_compaction,
        )

    def command(self, raw_args, *, session_id=""):
        if not self._native_id(session_id):
            return "Hermes 未提供当前会话 ID。" + MANUAL
        try:
            args = shlex.split(raw_args)
            if not ((len(args) == 3 and args[0] == "register")
                    or (len(args) == 2 and args[0] == "unregister")):
                return USAGE
            task = self.registrations.identifier(args[1])
            with self._locked_state() as state:
                binding = state.get(session_id, {})
                if binding is None:
                    return "当前会话已因压缩迁移，请在压缩后的会话操作。" + MANUAL
                storage_session = binding.get("storage_session", session_id)
                if args[0] == "register":
                    self.registrations.register_task(HOST, storage_session, task, Path(args[2]), self.home)
                    return f"已登记当前 Hermes 会话中的统筹任务 {task}。"
                self.registrations.unregister_task(HOST, storage_session, task, self.home)
                if binding.get("pending") and not self._context(storage_session, before_compaction=True):
                    state[session_id] = {**binding, "pending": False}
                    self._save(state)
                return f"已撤销当前 Hermes 会话中的统筹任务 {task}。"
        except (ArgumentTypeError, OSError, ValueError) as error:
            return f"更新统筹登记失败。{error} {MANUAL}"

    def post_compaction(self, session_id="", old_session_id="", kind=None, **_event):
        # Provider-owned turns, such as Codex app-server text turns, may drop hook context.
        if kind == "provider_native":
            return
        source = old_session_id or session_id
        if not self._native_id(session_id) or not self._native_id(source):
            return
        if not self.state_path.is_file() and not self.registrations.session_dir(HOST, source, self.home).is_dir():
            return
        with self._locked_state() as state:
            binding = state.get(source, {})
            if binding is None:
                return
            storage_session = binding.get("storage_session", source)
            if not self._context(storage_session, before_compaction=True):
                return
            if source != session_id:
                if session_id in state or self._context(session_id, before_compaction=True):
                    LOGGER.warning("Hermes 压缩续接目标已有独立绑定，请检查当前会话的协调记录。")
                    return
                # Keep the locators at their existing location. Retire the old native ID so a
                # replayed rotation or an old transcript cannot reactivate those registrations.
                state[source] = None
            state[session_id] = {"storage_session": storage_session, "pending": True}
            self._save(state)

    def pre_llm_call(self, session_id="", turn_id="", user_message=None, platform="", **_event):
        if platform == "subagent" or not turn_id or not isinstance(user_message, (str, list)) or not user_message:
            return None
        if not self._native_id(session_id) or not self.state_path.is_file():
            return None
        with self._locked_state() as state:
            binding = state.get(session_id)
            if not binding or not binding.get("pending"):
                return None
            context = self._context(binding["storage_session"])
            if binding["storage_session"] == session_id:
                del state[session_id]
            else:
                state[session_id] = {**binding, "pending": False}
            self._save(state)
            return {"context": context} if context else None


def register(ctx):
    from agent.skill_utils import parse_frontmatter
    from hermes_cli import plugins
    from hermes_constants import get_hermes_home

    if not callable(getattr(ctx, "register_skill", None)):
        LOGGER.warning("当前 Hermes 插件 API 无法原生加载技能 %s。%s", SKILL, MANUAL)
        return
    frontmatter, _ = parse_frontmatter(SKILL.read_text(encoding="utf-8"))
    ctx.register_skill(PLUGIN, SKILL, description=frontmatter["description"], frontmatter=frontmatter)

    if not callable(getattr(ctx, "register_command", None)):
        LOGGER.warning("当前 Hermes 插件 API 缺少会话命令。%s", MANUAL)
        return

    def unavailable(_args):
        return "当前 Hermes 运行时无法自动续接。" + MANUAL

    command = unavailable
    if callable(getattr(ctx, "register_hook", None)) and HOOKS <= getattr(plugins, "VALID_HOOKS", set()):
        try:
            recovery = _Recovery(get_hermes_home())
        except ImportError:
            LOGGER.warning("当前 Hermes 运行时缺少压缩续接依赖。%s", MANUAL)
        else:
            ctx.register_hook("post_compaction", recovery.post_compaction)
            ctx.register_hook("pre_llm_call", recovery.pre_llm_call)
            command = recovery.command
    else:
        LOGGER.warning("当前 Hermes 运行时缺少压缩续接事件。%s", MANUAL)

    ctx.register_command(COMMAND, command, "登记或撤销当前会话的统筹续接任务", args_hint="<动作> <任务ID> [记录路径]")
