# 宿主安装与续接

各宿主使用本插件的同一份 [SKILL.md](../SKILL.md) 和引用。插件目录是仓库内的 `plugins/ai-development-workflow/`。以下方式适用于已明确采用统筹的任务，登记时使用宿主确认的当前会话、稳定任务 ID 和可读的协调记录绝对路径。任务结束或接替生效后撤销相应登记。有在途任务时保留已确认的技能版本和责任边界。

## Cursor

在本地允许导入插件时，将整个插件目录复制到 `~/.cursor/plugins/local/ai-development-workflow/`，执行 Developer: Reload Window，并在 Customize 检查 Skill 和 Hook。使用 Cursor 确认的当前会话 ID，CLI 可通过 `/copy-conversation-id` 获取。由获准的负责人执行：

```sh
python3 -B <插件目录>/skills/ai-development-workflow/scripts/codex_compact.py --host cursor register <会话ID> <任务ID> <协调记录绝对路径>
python3 -B <插件目录>/skills/ai-development-workflow/scripts/codex_compact.py --host cursor unregister <会话ID> <任务ID>
```

`preCompact` 在压缩前向用户显示登记的恢复入口。压缩后在当前会话主动读取该记录、技能和适用引用，再按已确认分工继续。自动加载 Hook 以实际宿主为准，此路径用于本地 Cursor。

从 `0.11.1` 起，原生插件和从 Claude Code 导入的副本均使用修复版时，同一次压缩的重复调用只显示一份提示。该场景已在 Cursor 桌面 `3.31.15` 实测。宿主未提供 `generation_id` 或插件无法读写去重记录时，仍会显示恢复入口，可能重复提示。

## Pi

用 `pi install <插件目录绝对路径>` 加载本地包。用 `/skill:ai-development-workflow` 核对已加载的 Skill。获准的负责人在当前会话执行 `/ai-workflow-register <任务ID> "<协调记录绝对路径>"`，结束时执行 `/ai-workflow-unregister <任务ID>`。扩展从 Pi 读取当前会话 ID。成功压缩后，在下一次模型请求附恢复入口，包括同一轮因上下文溢出而重试的请求。新会话和 fork 依自身分工、授权及登记处理。

## Hermes Agent

将整个插件目录复制到当前 profile 的 `plugins/ai-development-workflow/`，再执行 `hermes plugins enable ai-development-workflow`。用 `skill_view` 读取 `ai-development-workflow:ai-development-workflow` 及其引用。获准的负责人在当前会话执行 `/workflow-coordinator register <任务ID> "<协调记录绝对路径>"`，结束时执行 `/workflow-coordinator unregister <任务ID>`。

插件 `0.11.1` 已在 Hermes `0.23.2`、`0.23.3`、`0.23.4` 验证普通 CLI 登记，以及通过宿主接口触发的压缩换号、重启续接和撤销。`0.23.4` 还通过了普通 CLI 的实际 `/compress` 验收。宿主换号后，压缩后的下一正常用户轮收到一次当前任务的记录入口，随后一轮没有重复注入。普通新会话、fork、子 Agent 和其他 profile 各自按本任务登记。插件 `0.11.0` 在 Hermes `0.23.3` 上需手动续接。

自动续接依赖宿主的 `post_compaction` 和 `pre_llm_call` 两个事件，以及可用的会话 ID 校验接口。登记命令提示缺少事件或依赖时，按提示从协调记录手动恢复分工、执行者和授权。同轮内需要立即恢复、使用 `provider_native` 压缩或 `codex_app_server` 文本模式时，也按此方式续接。其他插件若在提醒取出后阻断当轮模型请求，模型可能收不到提醒，届时请手动读取协调记录。

这些续接入口只提供范围和证据的定位。派单、回传和权限核查按[协作规则](coordination.md)及各宿主实际入口执行。专用 Codex 会话的派单校验见 [Codex 统筹保护](codex-coordinator.md)。
