"""Run from an installed Hermes Python environment with its source on PYTHONPATH."""

import json
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
from tempfile import TemporaryDirectory
from types import ModuleType, SimpleNamespace
from unittest.mock import Mock, patch


PLUGIN = "ai-development-workflow"
PACKAGE = Path(__file__).resolve().parents[2] / "plugins" / PLUGIN
COMMAND = "workflow-coordinator"
SKILL = f"{PLUGIN}:{PLUGIN}"
OLD = "20261119_100000_aaaaaa"
ACTIVE = "20261119_100001_bbbbbb"
NEXT = "20261119_100002_cccccc"
FORK = "20261119_100003_dddddd"
CHILD = "20261119_100004_eeeeee"
NEW = "20261119_100005_ffffff"


def install(profile):
    shutil.copytree(PACKAGE, profile / "plugins" / PLUGIN, ignore=shutil.ignore_patterns("__pycache__"))
    (profile / "config.yaml").write_text(f"plugins:\n  enabled:\n    - {PLUGIN}\n", encoding="utf-8")


def run_phase(phase, profile, root):
    env = os.environ.copy()
    env.update(HERMES_HOME=str(profile), PYTHONDONTWRITEBYTECODE="1")
    subprocess.run([sys.executable, "-B", __file__, phase, str(root)], cwd=root, env=env, check=True)


def verify_manual_command(module, *diagnostics):
    context = Mock()
    module.register(context)
    context.register_skill.assert_called_once()
    context.register_hook.assert_not_called()
    context.register_command.assert_called_once()
    name, handler, _description = context.register_command.call_args.args
    assert name == COMMAND
    notice = handler("register task-a /tmp/record.md")
    assert "手动续接" in notice and all(term in notice for term in diagnostics), notice


def verify(phase, root):
    expected = root / ("profile-b" if phase == "isolate" else "profile-a")
    assert Path(os.environ.get("HERMES_HOME", "")).resolve() == expected
    import hermes_cli
    from agent.compaction_events import fire_post_compaction, publish_attempt
    from agent.skill_utils import parse_frontmatter
    from agent.turn_context import _collect_pre_llm_call_context
    from hermes_cli import plugins
    from hermes_cli.plugin_command_dispatch import invoke_plugin_command
    from hermes_constants import get_hermes_home
    from tools.skills_tool import skill_view

    profile = get_hermes_home()
    plugins.discover_plugins()
    manager = plugins.get_plugin_manager()
    info = next(info for info in manager.list_plugins() if info["name"] == PLUGIN)
    assert info["enabled"] and info["hooks"] == 2 and info["commands"] == 1, info
    assert info["middleware"] == 0 and info["tools"] == 0, info
    skill_path = manager.find_plugin_skill(SKILL)
    assert skill_path == profile / "plugins" / PLUGIN / "skills" / PLUGIN / "SKILL.md"
    source = (PACKAGE / "skills" / PLUGIN / "SKILL.md").read_text(encoding="utf-8")
    frontmatter, _body = parse_frontmatter(source)
    metadata = next(item for item in manager.list_plugin_skill_metadata() if item["name"] == SKILL)
    assert metadata["frontmatter"] == frontmatter
    assert metadata["description"] == frontmatter["description"]
    skill = json.loads(skill_view(SKILL, preprocess=False))
    assert skill["success"] and skill["content"].endswith(source), skill.keys()
    reference = json.loads(skill_view(SKILL, "references/coordination.md", preprocess=False))
    assert reference["success"] and reference["content"], reference.keys()
    handler = plugins.get_plugin_command_handler(COMMAND)

    def command(session_id, args):
        return invoke_plugin_command(handler, args, session_id=session_id, platform="cli")

    def turn(session_id, *, platform="cli", parent="", user_message="continue"):
        agent = SimpleNamespace(session_id=session_id, platform=platform, model="test", _parent_session_id=parent)
        return _collect_pre_llm_call_context(
            agent, effective_task_id="host-turn", turn_id=f"{session_id}:turn",
            original_user_message=user_message, messages=[], conversation_history=[],
        )

    def compact(session_id, old="", kind="summarize"):
        fire_post_compaction(
            session_id=session_id, old_session_id=old, kind=kind, reason="manual",
            before_tokens=100, after_tokens=50, messages_removed=4,
        )

    record = root / "coordination record.md"
    second_record = root / "second record.md"
    if phase == "seed":
        # Normal Gateway CLI commands and hooks use physical IDs. The logical route stays
        # on the first ID even after compression rotates the physical transcript.
        local = "local-" + "0123456789abcdef" * 4
        rotated = "8da3f1929a084a3fb434355ec9e290bc"
        other = "8da3f1929a084a3fb434355ec9e290bd"
        register_local = f"register gateway-task {shlex.quote(str(record))}"
        for invalid in (f"agent:main:local:dm:{local}", local[:-1], local + "f", local.upper(),
                        rotated[:12] + "5" + rotated[13:], rotated[:16] + "7" + rotated[17:],
                        rotated.upper(), rotated + "f"):
            assert "手动续接" in command(invalid, register_local)
        assert "已登记" in command(local, register_local)
        compact(rotated, local)
        assert not turn(local) and not turn(other, parent=local)
        assert not turn(rotated, platform="subagent")
        assert "gateway-task" in turn(rotated)
        assert not turn(rotated)
        assert "已因压缩迁移" in command(local, "unregister gateway-task")
        assert "已撤销" in command(rotated, "unregister gateway-task")

        assert "手动续接" in command("agent:main:cli", f"register task-a {shlex.quote(str(record))}")
        assert "手动续接" in command("", f"register task-a {shlex.quote(str(record))}")
        assert "手动续接" in command(OLD, "register task-a relative.md")
        assert "已登记" in command(OLD, f"register task-a {shlex.quote(str(record))}")
        assert not turn(OLD)
        publish_attempt(SimpleNamespace(session_id=OLD), {"session_id": OLD, "commit_status": "aborted"})
        assert not turn(OLD)
        compact(OLD, kind="provider_native")
        assert not turn(OLD)
        compact(OLD)
        assert not turn(OLD, user_message=None)
        assert not turn(OLD, platform="subagent")
        for session in (NEW, FORK, CHILD):
            assert not turn(session, parent=OLD)
        notice = turn(OLD, user_message=[{"type": "text", "text": "continue"}])
        assert "task-a" in notice and str(record) in notice and "RECORD-BODY" not in notice
        assert not turn(OLD)
        compact(ACTIVE, OLD)
        assert not turn(OLD)
    elif phase == "isolate":
        assert not turn(OLD) and not turn(ACTIVE)
        assert "已登记" in command(ACTIVE, f"register task-b {shlex.quote(str(second_record))}")
        compact(ACTIVE)
        notice = turn(ACTIVE)
        assert "task-b" in notice and "task-a" not in notice and str(record) not in notice
    elif phase == "resume":
        assert not turn(OLD) and not turn(NEW) and not turn(FORK, parent=OLD)
        notice = turn(ACTIVE)
        assert "task-a" in notice and str(record) in notice and "task-b" not in notice
        assert not turn(ACTIVE)
        compact(ACTIVE, OLD)  # Replay of a rotation whose notice was already delivered.
        compact(OLD)  # Stale transcript still exists.
        assert not turn(ACTIVE) and not turn(OLD)
        assert "已因压缩迁移" in command(OLD, "unregister task-a")
        assert "已登记" in command(ACTIVE, f"register task-b {shlex.quote(str(second_record))}")
        compact(NEXT, ACTIVE)
        assert "已撤销" in command(NEXT, "unregister task-a")
        second_record.unlink()
        notice = turn(NEXT)
        assert "task-a" not in notice and "task-b" in notice and "不可读取" in notice
        compact(NEXT)
        assert "已撤销" in command(NEXT, "unregister task-b")
        assert not turn(NEXT)

        module = manager._plugins[PLUGIN].module
        with patch.object(plugins, "VALID_HOOKS", {"pre_llm_call"}):
            verify_manual_command(module, "post_compaction")
        with patch.dict(sys.modules, {"session_rules.session_ids": None, "hermes_state_ids": None}):
            verify_manual_command(module, "session_rules.session_ids", "hermes_state_ids")

        # A usable legacy module must not mask a failure inside the newer module.
        session_rules = ModuleType("session_rules")
        session_rules.__path__ = [str(root)]
        legacy = SimpleNamespace(is_known_session_id=lambda value: True)
        with patch.dict(sys.modules, {"session_rules": session_rules, "hermes_state_ids": legacy}):
            sys.modules.pop("session_rules.session_ids", None)
            (root / "session_ids.py").write_text("import missing_hermes_test_dependency\n", encoding="utf-8")
            verify_manual_command(module, "missing_hermes_test_dependency")
            (root / "session_ids.py").write_text("is_known_session_id = None\n", encoding="utf-8")
            verify_manual_command(module, "is_known_session_id")
    print(f"Hermes {hermes_cli.__version__} {phase} passed")


if __name__ == "__main__":
    if len(sys.argv) == 3:
        verify(sys.argv[1], Path(sys.argv[2]))
    else:
        with TemporaryDirectory(prefix="hermes-workflow-") as temp:
            root = Path(temp).resolve()
            home, other_home = root / "profile-a", root / "profile-b"
            install(home)
            install(other_home)
            (root / "coordination record.md").write_text("RECORD-BODY-A\n", encoding="utf-8")
            (root / "second record.md").write_text("RECORD-BODY-B\n", encoding="utf-8")
            run_phase("seed", home, root)
            run_phase("isolate", other_home, root)
            run_phase("resume", home, root)
