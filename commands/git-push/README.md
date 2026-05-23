# git-push

Code review + commit + push workflow for AI coding agents.

## 触发条件

用户说"帮我提交代码"、"commit"、"git push"、"审查并推送"时调用。

## 工作流

```
1. git status / git diff --stat / git diff
      ↓
2. Code Review（发现问题则停止）
      ↓
3. 生成 commit message
      ↓
4. git add <files>
5. git commit -m "<message>"
6. git push
```

## 规则

1. **先 review，后提交** — 执行 `git diff` 审查未提交代码
2. **发现问题立即停止** — 只输出问题与解决方案，**不修复、不提交、不推送**
3. **中文 body** — 描述变更背景、原因和关键实现
4. **Conventional Commits** — `<type>(<scope>): <subject>`

## 项目自适应身份

| 项目类型 | 身份 |
|---------|------|
| 前端/小程序 | 高级前端开发工程师 |
| 后端（Java/Go/Python等）| 高级后端开发工程师 |
| 其他 | 通用高级软件工程师 |

**必须优先遵循「当前项目规则文件」的约束。**

## 安装

```bash
# Claude Code
cp commands/git-push/SKILL.md ~/.claude/commands/git-push.md

# Cursor
cp commands/git-push/SKILL.md ~/.cursor/commands/git-push.md

# OpenCode
cp -r commands/git-push ~/.opencode/skills/

# Trae
cp commands/git-push/SKILL.md ~/.trae/commands/git-push.md
```

## License

MIT
