# HyperSpec:archive — 收尾阶段

## 目标

验证代码实现和规格文档的一致性，通过原生 skill 归档变更，完成整个开发周期。

## 前置检查

确认 apply 阶段已完成：

- `superpowers/plans/` 下的计划文件所有步骤已勾选
- 测试全部通过（或 test_command 为 null）
- 代码审查无 Critical 问题
- `.hyperspec-state.yaml` 中 `changes.<active_change>.checkpoint`（或旧格式顶层 `checkpoint`）为 `apply-done`、`consistency-verified`、`archived` 或 `done` 之一

如果前置条件不满足，提示：「apply 阶段尚未完成，请先运行 /hyperspec」

## 阶段流程

### 1. 规格一致性验证

逐项检查代码实现是否和规格文档一致。这是 HyperSpec 特有的验证环节，确保实现没有偏离设计。

**做法：**
- 读取 `openspec/changes/<变更名>/design.md`，逐一确认其中定义的技术方案是否在代码中体现
- 读取 `openspec/changes/<变更名>/specs/` 下的规格增量文件，确认每个 ADDED/MODIFIED/REMOVED 标记对应的代码变更确实存在
- 读取 `openspec/changes/<变更名>/tasks.md`，确认所有任务已完成
- 将验证结果整理为一份清单，逐项标注「通过」或「不一致」

验证维度：
- design.md 中定义的技术方案是否全部实现
- specs/ 中标记的 ADDED/MODIFIED/REMOVED 是否在代码中体现
- tasks.md 中的任务是否全部完成

**持久化验证状态**：验证完成后，在 `openspec/changes/<变更名>/` 下创建 `.close-verification-done` 文件（内容为验证结果清单），用于断点恢复时判断是否需要重跑验证。

完成后更新 `.hyperspec-state.yaml`：`changes.<active_change>.checkpoint: consistency-verified`。如当前变更仍是默认变更，可同步顶层 `checkpoint`。

### 2. 处理不一致

如果验证发现不一致，逐项列出并让用户选择：

**选项 A：改代码**
- 标记哪些代码需要修改
- 询问用户是否在本阶段直接修复（简单修复）或回到 apply 阶段（复杂修复）
- 如果用户选择回到 apply 阶段：更新 `.hyperspec-state.yaml` 为 `changes.<active_change>.phase: apply`、`changes.<active_change>.checkpoint: reviewed`，然后结束 archive 阶段

**选项 B：改规格**
- 标记哪些规格文档需要更新
- 更新 `openspec/changes/` 下的对应文件
- 重新走验证流程

**无论选择哪种修复方式，修复完成后必须：**
1. 删除 `.close-verification-done` 文件（使验证状态失效）
2. 更新 `.hyperspec-state.yaml`：`changes.<active_change>.checkpoint: apply-done`（回退到验证前）
3. 重新执行 Step 1 验证
4. 重新生成 `.close-verification-done`

验证结果全部通过后（或不一致项已修复并重新验证通过），进入 Step 3。

### 3. 调用 openspec-archive-change 归档

调用原生 `openspec-archive-change` skill，通过 CLI 执行归档。

**做法：**

1. 宣布："调用 openspec-archive-change 归档变更"
2. 使用可用的 Codex skill 机制调用 `openspec-archive-change`，args 格式：`<变更名>`。如果当前 Codex 会话没有该 skill，使用下方 CLI/文件操作降级方案。
3. `openspec-archive-change` 会自动执行：
   - 检查 artifact 完成状态（通过 CLI）
   - 检查 task 完成状态（读 tasks.md）
   - 评估 spec sync 状态（对比 delta specs 和主规格库）
   - 执行归档：`mv openspec/changes/<name> openspec/changes/archive/YYYY-MM-DD-<name>`
   - 展示归档摘要
4. 等待 skill 完成后，确认归档成功：检查 `openspec/changes/archive/` 下是否有对应目录，且原活跃变更目录已移除

**注意：** `openspec-archive-change` 内部可能包含用户确认环节（例如 Claude 环境中的 AskUserQuestion）。在 Codex 中，如果没有对应交互工具，就用简短自然语言向用户确认是否继续归档。但 Step 1 的验证结果应在调用 archive 前展示给用户。

**降级方案：** 如果 `openspec-archive-change` skill 不可用（Skill 工具返回 "Unknown skill"），手动执行归档操作：
1. 确认 `openspec/changes/<变更名>/tasks.md` 中所有任务已标记为完成
2. 确保 `openspec/changes/archive` 目录存在。在 Codex/Windows 中优先使用 PowerShell `New-Item -ItemType Directory -Force`。
3. 将 `openspec/changes/<变更名>` 移动到 `openspec/changes/archive/<YYYY-MM-DD>-<变更名>`。在 Codex/Windows 中优先使用 PowerShell `Move-Item -LiteralPath ...`，移动前验证源路径和目标路径都位于项目根目录内。
4. 确认归档成功：活跃变更目录已移除，archive 目录已创建

完成后更新 `.hyperspec-state.yaml`：`changes.<active_change>.checkpoint: archived`。如当前变更仍是默认变更，可同步顶层 `checkpoint`。

### 4. 分支收尾 + 总结

**如果使用了 worktree：**
提示用户选择分支处理方式：

1. **合并到主分支** — 在 worktree 中合并，清理 worktree
2. **创建 PR** — 推送到远程，创建 Pull Request
3. **保持现状** — 保留分支和 worktree，稍后处理
4. **丢弃** — 放弃所有改动（需输入 "discard" 确认）

**如果未使用 worktree（直接在当前分支开发）：**
跳过分支处理，提示用户是否需要提交代码。

**总结报告：**
向用户报告本次变更的完整信息：
- 完成了哪些任务
- 涉及哪些文件的改动
- 规格更新了什么
- 归档位置

**归档 brainstorm 摘要：**
如果项目根目录存在 `.hyperspec-brainstorm.md`，将其移动到本次变更的归档目录：

```text
openspec/changes/archive/<YYYY-MM-DD>-<变更名>/brainstorm.md
```

规则：
- 仅在归档目录已确认存在后移动，避免丢失需求决策上下文
- 如果目标文件已存在，先比较内容；一致则删除根目录副本，不一致则保留根目录副本并提示用户确认
- 如果本次没有经过 brainstorm 阶段，`.hyperspec-brainstorm.md` 不存在则跳过
- 不将 `.hyperspec-brainstorm.md` 长期留在项目根目录，避免下次变更误用过期摘要

**清理状态文件：**
更新 `.hyperspec-state.yaml`：`changes.<active_change>.checkpoint: done`，然后清理当前变更分区：

1. 删除 `changes.<active_change>`。
2. 如果 `changes` 中还有其他活跃变更，保留 `.hyperspec-state.yaml`，并将 `active_change` 切换到剩余变更之一，或设为 `null` 让下一次运行显式指定 `--change`。
3. 如果 `changes` 已为空，且没有需要保留的运行态信息，删除 `.hyperspec-state.yaml`。

如果用户接受 HyperSpec 自动 commit 纪律，将状态文件的删除或修改纳入同一个收尾 commit；如果 `.hyperspec-brainstorm.md` 已移动到归档目录，也将该移动纳入同一个收尾 commit（message: `chore: hyperspec <变更名> 完成`）。如果用户未确认自动 commit，则停在可提交状态并报告需要提交的文件。

## 出口条件

- 实现和规格一致（验证通过）
- 变更已归档（由 openspec-archive-change 完成）
- 如使用了 worktree：用户已选择分支处理方式且 worktree 已处理
- 如未使用 worktree：代码已提交或用户已确认稍后处理
- 当前变更的 `changes.<active_change>` 状态分区已清理；若无其他活跃变更，`.hyperspec-state.yaml` 已删除
- 如存在 `.hyperspec-brainstorm.md`：已移动到归档目录的 `brainstorm.md`，或用户确认保留/处理方式

## 断点恢复

archive 阶段可能通过两种方式进入：
1. apply 阶段完成后自动进入（正常路径）
2. 用户显式指定「归档收尾」进入（用户意图覆盖）

重新运行时，读取 `.hyperspec-state.yaml` 中 `changes.<active_change>.checkpoint`；没有对应分区时，才回退到顶层 `checkpoint`。随后验证：

| checkpoint | 实际状态验证 | 恢复到 |
|-----------|-------------|--------|
| `apply-done` | `.close-verification-done` 不存在 | Step 1（验证） |
| `consistency-verified` | `.close-verification-done` 存在且归档目录不存在 | Step 3（归档） |
| `consistency-verified` | `.close-verification-done` 不存在（被手动删除） | Step 1（重跑验证） |
| `apply-done` | `.close-verification-done` 存在（与 checkpoint 不一致，以文件为准） | 检查归档目录是否存在，存在则 Step 4，不存在则 Step 3 |
| `archived` | 归档目录存在但分支未处理 | Step 4（分支收尾） |
| `archived` | 归档目录不存在（归档中断） | Step 3（重做归档） |
| `archived` | 归档目录存在且根目录有 `.hyperspec-brainstorm.md` | Step 4（归档 brainstorm 摘要并清理） |
| `archived` | 归档目录存在且分支已处理 | 展示变更摘要（同 Step 4 总结报告），然后清理当前变更状态分区完成 |

**异常状态检测：**
- 活跃变更目录已删除但 archive 目录不存在 → 归档过程中断，提示用户可尝试 `openspec list --json` 检查状态
- `.hyperspec-state.yaml` 存在但活跃变更目录不存在且未归档 → 可能是手动删除，提示用户确认状态

## 硬门

本阶段如果发现需要改代码，简单的修复可以直接做（不影响规格的 bug 修复）；但如果改动会影响规格定义，必须回到 apply 阶段。
