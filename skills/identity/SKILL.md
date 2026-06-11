---
name: identity
description: 检测项目类型并设定 Agent 身份，支持前端/后端/全栈/移动端/数据科学/DevOps 等类型识别
---

# identity

Detect project type: script fingerprint → AI decision. Fallback to deep inspection when ambiguous.

## 步骤

### 1. 采集指纹

```bash
bash detect.sh [project-root]
```

得到 JSON：`{"files":[...], "deps":[...], "subs":[...]}`

### 2. 读上下文（辅助判断）

快速扫一眼这些文件（存在则读）：
- `CLAUDE.md` / `AGENTS.md` — 通常有人工写的项目描述
- `README.md` — 项目名、简介
- `package.json` 的 `name` / `description` 字段

### 3. 决策

根据 `files` + `deps` + 上下文信息判断：

**类型判定：**

```
src/App.vue|.tsx|.jsx 或 vite.config|vue.config|next.config|nuxt.config|angular.json|astro.config|remix.config|svelte.config 且 package.json → 前端

go.mod|pom.xml|Cargo.toml|pyproject.toml|requirements.txt|composer.json|Gemfile|mix.exs 且 package.json 或无 → 后端

前两者同存 → 全栈

pubspec.yaml|AndroidManifest|*.xcodeproj → 移动端

*.ipynb 或 deps 含 torch|tensorflow → 数据科学

仅 Dockerfile|docker-compose → DevOps

仅 hugo|config.toml|_config.yml → 静态站点

turbo.json|nx.json|lerna.json|pnpm-workspace → monorepo（检查 subs，递归首个子项目）

仅 package.json + src/ 无框架特定文件 → 前端/Node.js

仅 package.json 无 src/ — 看 deps：含 vue|react|angular|svelte|webpack|vite → 前端；含 express|fastify|koa|hono → Node.js 后端

仅 *.php → PHP 项目（检查 composer.json 或 README 确认框架）

仅 package.json + tsconfig.json，deps 含 jest|webpack|babel 等工具链 → TypeScript 库/工具项目
```

**框架：** deps 首个匹配：next→Next.js, nuxt→Nuxt, vue→Vue, react→React, svelte→Svelte, @angular/core→Angular, astro→Astro, express→Express, fastify→Fastify, @nestjs/core→NestJS, django→Django, fastapi→FastAPI, flask→Flask。文件兜底：go.mod→Go, Cargo.toml→Rust, pom.xml→Java, composer.json→PHP, artisan→Laravel, Gemfile→Ruby。

**语言：** tsconfig.json→TS, go.mod→Go, Cargo.toml→Rust, pyproject.toml→Python, composer.json→PHP, Gemfile→Ruby, pom.xml→Java, pubspec.yaml→Dart, *.php→PHP。否则 package.json→JS。

**PHP 特殊判断：** files 含 `*.php` 时检查 `composer.json`。有→Composer 项目。无 `composer.json` 但有 `application/` 或 `boot.php` → 自研框架 PHP。

### 4. 兜底：逐目录检查

如果以上都无法判断（结果为"未知"或通用身份），放弃脚本，执行：

```bash
ls -la [root]
ls [root]/*/  2>/dev/null | head -20
```

根据实际目录结构（框架名、配置文件、语言文件）直接判断项目类型。

### 5. 输出

```
## 项目类型识别
- 类型：前端 (Vue)
- 框架：Vue
- 语言：TypeScript
- 身份：高级前端开发工程师
- 判断依据：package.json, vite.config.ts, src/App.vue
```

Monorepo 标注子项目路径。

## 身份持久化

身份设定后本会话持续生效。
