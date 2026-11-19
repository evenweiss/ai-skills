# 宿主安装与续接

各宿主使用本插件的同一份 [SKILL.md](../SKILL.md) 和引用。插件目录是仓库内的 `plugins/ai-development-workflow/`。以下方式适用于已明确采用统筹的任务，登记时使用宿主确认的当前会话、稳定任务 ID 和可读的协调记录绝对路径。任务结束或接替生效后撤销相应登记。有在途任务时保留已确认的技能版本和责任边界。

## Cursor

在本地允许导入插件时，将整个插件目录复制到 `~/.cursor/plugins/local/ai-development-workflow/`，执行 Developer: Reload Window，并在 Customize 检查 Skill 和 Hook。使用 Cursor 确认的当前会话 ID，CLI 可通过 `/copy-conversation-id` 获取。由获准的负责人执行：

```sh
python3 -B <插件目录>/skills/ai-development-workflow/scripts/codex_compact.py --host cursor register <会话ID> <任务ID> <协调记录绝对路径>
python3 -B <插件目录>/skills/ai-development-workflow/scripts/codex_compact.py --host cursor unregister <会话ID> <任务ID>
```

`preCompact` 在压缩前向用户显示登记的恢复入口。压缩后在当前会话主动读取该记录、技能和适用引用，再按已确认分工继续。自动加载 Hook 以实际宿主为准，此路径用于本地 Cursor。

## Pi

用 `pi install <插件目录绝对路径>` 加载本地包。用 `/skill:ai-development-workflow` 核对已加载的 Skill。获准的负责人在当前会话执行 `/ai-workflow-register <任务ID> "<协调记录绝对路径>"`，结束时执行 `/ai-workflow-unregister <任务ID>`。扩展从 Pi 读取当前会话 ID。成功压缩后，在下一次模型请求附恢复入口，包括同一轮因上下文溢出而重试的请求。新会话和 fork 依自身分工、授权及登记处理。

## Hermes Agent

使用支持 `post_compaction` 的 Hermes Agent，本项目的验收基线为 v0.23.2。将整个插件目录复制到当前 profile 的 `plugins/ai-development-workflow/`，再执行 `hermes plugins enable ai-development-workflow`。可用 `skill_view` 读取 `ai-development-workflow:ai-development-workflow` 及其引用。获准的负责人在当前会话执行 `/workflow-coordinator register <任务ID> "<协调记录绝对路径>"`，结束时执行 `/workflow-coordinator unregister <任务ID>`。

通用 Hermes 运行时在成功压缩后的下一用户轮注入恢复入口。同一用户轮内的即时恢复，以及 `codex_app_server` 模式，沿用手动续接。宿主在压缩时更换会话 ID，按该次事件关联实际延续的会话。普通新会话、fork 或子 Agent 不沿用原登记。

这些续接入口只提供范围和证据的定位。派单、回传和权限核查按[协作规则](coordination.md)及各宿主实际入口执行。专用 Codex 会话的派单校验见 [Codex 统筹保护](codex-coordinator.md)。
