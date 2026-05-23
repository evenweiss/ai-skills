# git-commit-msg

> Generate commit message from git diff, and optionally execute git commit

**触发条件：** 当需要"生成提交信息"、"写 commit message"、"帮我写 commit"、"生成几个 commit 建议"时调用。

## 使用方式

1. 执行 `git diff` 获取变更内容
2. 分析变更文件路径和内容，判断变更类型
3. 根据 Conventional Commits 规范生成 commit message
4. 输出生成的 commit message 供用户审阅
5. 询问用户是否以当前生成的 message 进行 commit
6. 如果用户回复"是"、"同意"、"确认"等肯定词，则执行 `git commit`；否则不执行

**注意：** 如需生成后直接提交（无需询问），请使用 `git-commit`。

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
| wip | 开发中（未完成）|

## 判断规则

- 变更文件在 `docs/` → `docs`
- 变更包含 `*.test.ts` / `*.spec.ts` / `__tests__/` → `test`
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
- src/middleware/auth.ts

---

原始 diff 摘要：
+120 行 / -30 行
```

## 可选提交

生成 commit message 后，询问用户：`是否以该 message 进行 commit？`

- 用户回复"是"、"同意"、"确认"、"好"等肯定词 → 执行提交
- 用户回复否定或要求修改 → 不执行，等待用户进一步指示

执行命令：

```bash
git commit -m "<type>(<scope>): <subject>" -m "<body>"
```

- 如果 body 为空，省略第二个 `-m` 参数
- 执行后输出 commit 结果（含 commit hash）
- 如果 commit 失败，输出错误信息供用户排查

### 注意事项

- 提交前先确认 `git add` 已完成（检查 `git status` 是否有未暂存变更）
- 如果有未暂存变更，提醒用户是否需要 `git add`，不要自动执行
- 不要使用 `git commit -a`，避免意外提交不相关的文件

## Conventional Commits 格式规范

```
<type>(<scope>): <subject>

<body>
```

- `type` 小写
- `scope` 可选，用小写字母
- `subject` 首字母小写，结尾不加句号
- `body` 使用中文，描述变更背景、原因和关键实现
- 标题和 body 之间空一行
