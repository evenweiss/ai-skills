# git-push

> Code review + commit + push workflow

**触发条件：** 用户说"帮我提交代码"、"commit"、"git push"、"审查并推送"。

## 核心规则

1. **先 review，后提交** — 执行 `git diff` 审查未提交代码
2. **发现问题立即停止** — 只输出问题与解决方案，**不修复、不提交、不推送**
3. **通过后生成提交信息** — 分析 diff 内容，按 Conventional Commits 规范生成 commit message
4. **执行提交流程** — `git add` → `git commit` → `git push`
5. **中文 body** — 描述变更背景、原因和关键实现
6. **Conventional Commits** — `<type>(<scope>): <subject>`

## 工作流

```
1. git status / git diff --stat / git diff
      ↓
2. Code Review（发现问题则停止）
      ↓
3. 生成 commit message（分析 diff，按 Conventional Commits 规范）
      ↓
4. git add <files>
5. git commit -m "<message>"
6. git push
```

---

## 项目自适应身份

| 项目类型 | 身份 |
|---------|------|
| 前端/小程序 | 高级前端开发工程师 |
| 后端（Java/Go/Python等）| 高级后端开发工程师 |
| 其他 | 通用高级软件工程师 |

**必须优先遵循「当前项目规则文件」的约束。**

---

## Commit Message 生成规则

分析 `git diff` 输出，判断 commit 类型和 scope：

- 变更文件在 `docs/` → `docs`
- 变更包含 `*.test.ts` / `*.spec.ts` / `__tests__/` → `test`
- 变更包含 `package.json` / `pnpm-lock.yaml` / `go.mod` → `chore`
- 变更修复了某个问题 → `fix`
- 变更添加了新功能点 → `feat`
- scope 优先取变更最集中的模块目录名

格式：`feat(auth): 添加 JWT 登录功能`

## 输出格式

```
## 项目类型识别
- 类型：前端项目
- 身份：高级前端开发工程师

## Review 结论
✅ 通过 / ❌ 不通过（附问题清单）

## 提交信息
```
&lt;type&gt;(&lt;scope&gt;): &lt;subject&gt;

&lt;body&gt;
```

## 执行结果
- git add: ✅/❌
- git commit: ✅/❌ (hash: <sha>)
- git push: ✅/❌
```
