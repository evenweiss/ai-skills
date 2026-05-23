# git-commit-msg

Smart commit message generator with Conventional Commits format.

## 触发条件

需要"生成提交信息"、"写 commit message"、"帮我写 commit"时调用。

## 功能

分析 `git diff` 输出，生成符合 Conventional Commits 规范的 commit message。

## Conventional Commits 类型

| type | 使用场景 |
|------|---------|
| feat | 新功能 |
| fix | 修复 bug |
| docs | 文档更新 |
| style | 代码格式（不影响功能）|
| refactor | 重构（不影响功能）|
| perf | 性能优化 |
| test | 测试相关 |
| chore | 构建/工具/依赖更新 |

## 判断规则

- 变更文件在 `docs/` → `docs`
- 变更包含 `*.test.ts` / `*.spec.ts` → `test`
- 变更包含 `package.json` / `pnpm-lock.yaml` / `go.mod` → `chore`
- 变更修复了某个问题 → `fix`
- 变更添加了新功能点 → `feat`
- scope 优先取变更最集中的模块目录名

## 输出格式

```
## 提交信息建议

**type:** feat
**scope:** auth
**subject:** 添加 JWT 登录功能

**body:**
实现基于 JWT 的用户登录鉴权流程，包含 token 生成、验证和刷新机制。

变更文件：
- src/auth/login.ts
- src/auth/jwt.ts
```

## 安装

```bash
# Claude Code
cp commands/git-commit-msg/SKILL.md ~/.claude/commands/git-commit-msg.md

# Cursor
cp commands/git-commit-msg/SKILL.md ~/.cursor/commands/git-commit-msg.md

# OpenCode
cp -r commands/git-commit-msg ~/.opencode/skills/

# Trae
cp commands/git-commit-msg/SKILL.md ~/.trae/commands/git-commit-msg.md
```

## License

MIT
