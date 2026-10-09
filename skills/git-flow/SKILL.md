---
name: git-flow
description: Create, check out, or finish Git Flow feature, release, and hotfix branches; not for generic Git operations or read-only Git questions.
---

# Git Flow

此流程与原始 Git Flow 不同：三类新分支都从最新生产主干创建，finish 都发布到生产主干并合入 `develop`。生产主干是仓库实际使用的 `master` 或 `main`；先确认 remote 和主干，不自行切换发布线或创建 worktree。用户本次的明确限制优先于本 skill；流程描述本身不替代当前任务对提交、远端写入和删除的授权。

| 类型 | 新分支 | finish 的 Tag |
| --- | --- | --- |
| feature | `feature/<功能简称>` | 远端生产主干可达的最高 `X.Y.Z` Tag → `X.(Y+1).0` |
| release | `release/X.Y.Z`；未提供目标版本时询问 | 分支名中的 `X.Y.Z` |
| hotfix | `hotfix/X.Y.Z`；创建时按远端 Tag 与 hotfix 分支计算 | 远端生产主干可达的最高 `X.Y.Z` Tag → `X.Y.(Z+1)`，可能与分支名不同 |

版本按三个数字段比较，只接受严格的 `X.Y.Z`。使用 [版本计算脚本](scripts/version.py) 获取创建 hotfix、release 校验及三类 finish 的候选版本；先获取最新远端生产主干、分支和 Tag，再在仓库根目录运行。脚本只读本地 Git 和实时远端引用，输出一行 JSON，不创建分支、提交或 Tag。`status=error` 时停止并处理原因；`status=needs_review` 时展示依据并暂停确认，不自行改算。没有合格 Tag、版本线或格式约定不明时暂停核对；不得猜测、覆盖 Tag 或重写历史。release 目标版本须高于远端生产主干的最高版本 Tag。

## 按任务读取

- 新建或检出已有分支：读 [创建与检出](references/create.md)。
- 完成分支：读 [Finish](references/finish.md)。

结束时报告实际分支、版本 Tag、已推送及已删除的引用；失败时列明已完成和未完成的步骤。
