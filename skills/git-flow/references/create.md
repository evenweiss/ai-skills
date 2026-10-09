# 创建与检出

## 已有分支

用户要求检出已有分支时，确认本地、远端和现有 worktree 的占用状态，检出指定本地分支或跟踪同名远端分支。不要生成新版本、新分支或推送。切换可能覆盖改动时暂停；不自动 stash、reset 或覆盖。

## 新分支

1. 确认仓库、remote、生产主干、工作区和暂存区干净，且无未完成的 Git 操作或同名本地分支。获取最新远端生产主干、远端分支和 Tag。若本地生产主干落后，只允许快进到远端提交；若超前、分叉、有未提交改动或更新失败，暂停，不把未发布提交混入起点。三类分支均从核实后的最新生产主干提交创建，不从 `develop` 或旧 Tag 创建。
2. feature 使用用户给出的功能简称。release 使用用户指定的目标 `X.Y.Z`；未指定时先询问，不自动递增。hotfix 和 release 的版本计算/校验调用 `scripts/version.py`（路径相对本 skill 目录）：

   ```sh
   python3 "$skill_dir/scripts/version.py" create-hotfix --repo . --remote origin --production master
   python3 "$skill_dir/scripts/version.py" create-release --repo . --remote origin --production master --branch release/1.2.3
   ```

   将 `skill_dir` 设为本 skill 的绝对目录，并将示例中的 remote、生产主干、release 版本替换为当前仓库的实际值。

   hotfix 候选取远端生产主干可达的最高 `X.Y.Z` Tag 与远端严格匹配 `hotfix/X.Y.Z` 的最高分支版本，按数字比较并对较大者的补丁段加 1。展示脚本返回的依据与候选名；未事先明确版本时创建前取得确认，已明确版本时核对它符合规则而不重复询问。脚本 `needs_review` 或版本线、占用状态不明时暂停；`error` 时不要绕过脚本自行猜版本。创建阶段不写 CHANGELOG 占位内容或发布 Tag。
3. 用 `git check-ref-format --branch` 校验完整名称，确认本地与远端均无同名分支，然后创建并检出。再次确认远端同名 ref **明确不存在**；查询或认证失败不能当作不存在。除非用户本次限定仅本地，创建后立即只新建同名远端 ref：

   ```sh
   git push --porcelain --no-follow-tags --force-with-lease=refs/heads/<分支名>: <remote> HEAD:refs/heads/<分支名>
   ```

   空的 lease 期望值要求远端 ref 仍不存在；不得添加 `--force` 或 `+`，也不能换成普通 push。仅 porcelain `*` 表示新建成功；`=` 也按重名处理。成功后回读远端 SHA，设置同名 upstream。若已存在或并发抢先创建，保留本地分支，停止推送，告知用户该名称可能被他人占用并需换名；不覆盖、接管或自行改名。
