# ai-skills

公共 AI agent 技能和插件仓库。普通技能适用于 Claude Code、Codex、Cursor、Hermes Agent、OpenCode、Trae 等支持 SKILL 规范的工具。AI 开发协作插件提供 Codex、Claude Code、Cursor、Pi 和 Hermes Agent 的宿主入口。

## 技能列表

### Commands

| ID | 能力 |
| --- | --- |
| [git-push](commands/git-push/SKILL.md) | 代码审查 → 生成提交信息 → commit → push 完整工作流；带授权边界与 UI 改动截图自检规则 |

### Skills

| ID | 能力 |
| --- | --- |
| [git-flow](skills/git-flow/SKILL.md) | Git Flow feature / release / hotfix 分支的创建、检出与 finish：从生产主干建分支，版本号自动计算，finish 合并主干 + develop 并打 Tag |
| [identity](skills/identity/SKILL.md) | 检测项目类型（前端/后端/全栈/移动端/数据科学/DevOps 等），自动设定 agent 身份 |
| [generate-refactor-docs](skills/generate-refactor-docs/SKILL.md) | 为页面、直连接口及关联后端重构生成本地 Markdown 需求、契约、方案和验收用例 |

每个技能的详细用法见其目录下的 `SKILL.md`。

## 插件

[ai-development-workflow](plugins/ai-development-workflow/) 提供跨会话开发协作、压缩续接与独立验收。通过 Luminae Helper 安装：

```sh
luminae-helper plugin install ai-development-workflow --tool codex
luminae-helper plugin install ai-development-workflow --tool claude-code
```

开发时可在本仓库根目录注册本地 marketplace，并安装 `ai-development-workflow@ai-skills`：

```sh
codex plugin marketplace add .
codex plugin add ai-development-workflow@ai-skills

claude plugin marketplace add .
claude plugin install ai-development-workflow@ai-skills
```

发布后验收本机 Codex 的安装或升级结果时，按[Hook 核验说明](plugins/ai-development-workflow/skills/ai-development-workflow/references/codex-coordinator.md#启用)检查所用 Hook 的来源、启用和信任状态。Cursor、Pi 和 Hermes Agent 的安装、续接和适用条件见[宿主安装与续接](plugins/ai-development-workflow/skills/ai-development-workflow/references/host-adapters.md)。原来安装的独立 Skill 可通过各宿主或 Helper 的卸载入口移除。

## 普通技能安装

### 1. Helper 工具安装（推荐）

交互式勾选、自动适配各工具目录、自动处理 command/skill 模式转换：

```sh
npx luminae-helper
```

### 2. 人工安装

把对应条目复制到目标工具的目录即可，无需任何构建：

```sh
git clone https://github.com/evenweiss/ai-skills.git

# 例：给 Claude Code 安装 git-push（command 模式）
cp ai-skills/commands/git-push/SKILL.md ~/.claude/commands/git-push.md

# 例：给 Codex 安装 git-flow（skill 模式，整个目录）
cp -R ai-skills/skills/git-flow ~/.codex/skills/
```

各工具目录约定：

| 工具 | command | skill |
| --- | --- | --- |
| Claude Code | `~/.claude/commands/*.md` | `~/.claude/skills/*/` |
| Codex | — | `~/.codex/skills/*/` |
| Cursor | — | `~/.cursor/skills/*/` |
| Hermes Agent | — | `~/.hermes/skills/*/` |
| OpenCode | — | `~/.opencode/skills/*/` |

只支持 skill 的工具安装 command 条目时，把 `SKILL.md` 包装成同名目录即可（目录内放该文件）。

### 3. AI 智能安装

让工具里的 agent 自己装。把下面这段贴给你的 AI 编程工具：

```text
从 https://github.com/evenweiss/ai-skills 安装 <技能ID>：
用 git clone --depth 1 或 raw.githubusercontent.com 拉取 commands/<技能ID>（或 skills/<技能ID>），
按你的技能目录规范安装（如 Claude Code 的 ~/.claude/commands 或 ~/.claude/skills），
安装后列出文件清单确认。
```

## 目录结构

```text
commands/<id>/SKILL.md  # command 模式条目
skills/<id>/SKILL.md    # skill 模式条目（可含 references/ scripts/ 等附属文件）
plugins/<id>/           # 插件清单、Hook 和插件内使用的技能
```

## 下游消费者

下游工具从本仓库获取对应内容：

- [luminae-helper](https://github.com/evenweiss/luminae-helper) — 按正式 Tag 获取公共技能，打包时从本仓库读取插件
- 内部包装器（私有仓库，可内联附加技能后打包分发）
