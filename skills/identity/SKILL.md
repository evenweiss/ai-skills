---
name: identity
description: 检测项目类型并设定 Agent 身份，支持前端/后端/全栈/移动端/数据科学/DevOps 等类型识别
---

# identity

Detect project type and set agent identity. All detection logic is in `detect.sh` — zero AI inference.

## 执行

直接运行同目录下的 `detect.sh`：

```bash
bash detect.sh [project-root]
```

如果找不到脚本，用以下命令定位：

```bash
bash $(find ~/.cursor/skills/identity ~/.claude/commands/identity ~/.opencode/skills/identity -name detect.sh 2>/dev/null | head -1) [project-root]
```

脚本输出即身份报告，无需 AI 判断。

## 身份持久化

身份设定后本会话持续生效。
