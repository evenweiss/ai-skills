# identity

Detect project type and set agent identity - foundation for all tasks.

## 触发条件

用户说"检测项目类型"、"识别项目"、"设定身份"、"我是前端/后端工程师"时调用。

## 功能

1. **检测项目类型** — 扫描项目根目录及子目录文件结构，判断是前端/后端/全栈/移动端/数据科学/DevOps 等
2. **设定身份** — 根据项目类型返回匹配的 agent 身份描述
3. **输出项目信息** — 包含框架、语言、测试、CI 等元数据

## 项目类型判断规则

| 关键文件 | 项目类型 | 身份 |
|---------|---------|------|
| `package.json` + `src/` 或 `components/` | 前端 | 高级前端开发工程师 |
| `go.mod` | Go 后端 | 高级后端开发工程师 |
| `pom.xml` / `build.gradle` | Java 后端 | 高级后端开发工程师 |
| `requirements.txt` / `pyproject.toml` + 非 notebook | Python 后端 | 高级后端开发工程师 |
| 多种类型文件同时存在 | 全栈 | 高级全栈开发工程师 |
| `*.xcodeproj` / `*.xcworkspace` | iOS/macOS | 高级移动端开发工程师 |
| `notebook/*.ipynb` + `torch`/`tensorflow` | 数据科学 | 高级数据科学工程师 |
| 无法判断 | 未知 | 通用高级软件工程师 |

## 输出格式

```
## 项目类型识别
- 类型：前端（Vue）
- 框架：Vite + Vue 3
- 语言：TypeScript
- 身份：高级前端开发工程师，精通 Vue 3 + TypeScript + Vite
- 判断依据：检测到 package.json、vite.config.ts、src/App.vue
```

## 安装

```bash
# Claude Code
cp commands/identity/SKILL.md ~/.claude/commands/identity.md

# Cursor
cp commands/identity/SKILL.md ~/.cursor/commands/identity.md

# OpenCode
cp -r commands/identity ~/.opencode/skills/

# Trae
cp commands/identity/SKILL.md ~/.trae/commands/identity.md
```

## License

MIT
