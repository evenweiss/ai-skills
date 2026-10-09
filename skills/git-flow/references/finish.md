# Finish

按以下顺序执行。任何本次请求中的明确限制优先于默认流程。

1. **预检与定版：** 确认源分支、remote、生产主干、`develop`、工作区/暂存区、待合并提交及未完成 Git 操作。获取最新远端分支和 Tag；本地目标落后时只快进，有分叉或未发布本地提交时暂停查明。确认远端源分支未被他人推进。按源分支类型运行 `scripts/version.py`（路径相对本 skill 目录），使用其 `candidate` 作为 Tag，不自行重新计算：

   ```sh
   python3 "$skill_dir/scripts/version.py" finish-feature --repo . --remote origin --production master --branch feature/shop_notice
   python3 "$skill_dir/scripts/version.py" finish-hotfix --repo . --remote origin --production master --branch hotfix/1.2.4
   python3 "$skill_dir/scripts/version.py" finish-release --repo . --remote origin --production master --branch release/1.3.0
   ```

   将 `skill_dir` 设为本 skill 的绝对目录，并将示例中的 remote、生产主干、源分支替换为当前仓库的实际值。

   脚本 `error` 时停止，`needs_review` 时暂停确认；随后检查本地是否也存在同名 Tag、重复合并或发布。hotfix 的最终 Tag 可与创建时的分支名不同；若候选 Tag 对应其他进行中的 hotfix/release 或版本线不明，暂停询问。
2. **在源分支完成 CHANGELOG：** 首次合并前核对本次实际变化和 `CHANGELOG.md`，尤其是开发期间写入的 `[Unreleased]`。文件不存在时新建最小日志，以 `# Changelog` 和 `## [X.Y.Z] - YYYY-MM-DD` 起始，其中版本取第 1 步结果、日期取本次发布日期；只记录从本次发布起可核实的变化，不追溯补写此前版本、日期或条目。feature 记录实际功能或行为变化（如 `Added`、`Changed`），hotfix 记录实际修复（如 `Fixed`），release 汇总自上一生产 Tag 以来本版本尚未记录的显著变化；优化表述、分类、去重，不照搬分支名或提交日志。release 若已有与 `release/X.Y.Z` 一致且内容正确的版本节，保留版本号；若缺失、仍为 `[Unreleased]` 或写错版本号，把属于本次发布的内容整理到正确的 `[X.Y.Z]` 节，并按项目格式填写发布日期。其他未来版本内容留在 `[Unreleased]`；已有目标节则合并去重，不创建重复标题。内容或归属无法核实、其他改动无法安全隔离时暂停询问；无显著变化时不编造条目。

   **合并门槛：** 若需改动，保持检出源分支，只暂存 `CHANGELOG.md` 并创建一个独立提交；核对当前分支、提交 SHA 和该提交的文件清单，仅包含预期 CHANGELOG 改动后才可切换目标分支。不得在目标分支补写，也不得携带未提交的 CHANGELOG 改动进入合并。无需改动时不制造空提交。
3. **先完成两次本地合并：** 确认生产主干仍是远端最新提交，以 `git merge --no-ff <源分支>` 合入生产主干；在该合并提交创建附注版本 Tag；单行 message 使用 `Release <版本> <摘要>`，摘要依据本次 CHANGELOG 和实际改动概括主要内容，不得只写 `Release <版本>`；整条 message 不超过 50 个字符（含空格、标点）。创建后回读 message、长度和 Tag 指向，再运行相关项目检查。再更新本地 `develop` 到远端最新提交，以 `git merge --no-ff <同一源分支>` 合入，核对它包含源提交并运行相关检查。在两次合并和检查都成功前，不推送任一目标分支或 Tag。
4. **依次发布：** 再次核对远端目标 ref 和 Tag 未变化。先推送 `develop` 并回读确认，再推送生产主干和 Tag 并回读确认；生产主干与 Tag 优先原子推送，不支持时逐项核对。不得强推或覆盖已有 Tag。
5. **处理失败：** 任一合并冲突立即暂停并保留现场，报告目标、冲突文件、`git status` 摘要及已完成的提交、Tag、推送；不自动解冲突、abort、继续发布或删除源分支。检查或推送失败也暂停，报告已改变的引用和剩余步骤；已推送的引用不自动回滚。用户处理后重新核查远端状态再继续。
6. **清理源分支：** 仅当生产主干、Tag 和 `develop` 全部推送且回读验证后，自动删除远端及本地源分支，无需再次询问。先确认远端两个目标分支都包含源提交并读取远端源 ref 的确切 SHA；仅在它仍等于该 SHA 时条件删除，例如 `git push --force-with-lease=refs/heads/<源分支>:<SHA> <remote> :refs/heads/<源分支>`，不得加 `--force` 或 `+`。远端删除成功后用 `git branch -d <源分支>` 删除本地；任一验证或删除失败则停止并报告保留的引用，不强制删除。
