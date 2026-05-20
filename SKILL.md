---
name: hyperspec
description: 带头脑风暴前置的规格驱动+工程纪律完整开发工作流。协调OpenSpec（规格管理）和Superpowers（brainstorming、TDD、子代理审查），从想法澄清到规格、实现、归档一条流程走完。当用户说「用hyperspec」「规格驱动开发」「完整流程开发功能」「先头脑风暴再做规格」时触发。前提：需已安装Superpowers和OpenSpec。
---

# HyperSpec

规格驱动 + 工程纪律的完整开发工作流。协调 OpenSpec（规格管理）和 Superpowers（brainstorming + TDD + 子代理审查），从想法澄清到需求、实现、归档一条流程走完。

OpenSpec 管「做什么和为什么」，Superpowers 管「怎么做和做得对不对」。HyperSpec 是**纯编排层**，只做状态检测、阶段路由、commit 纪律，不重写任何原生 skill 的功能。

## Codex 运行约定

在 Codex 中使用 HyperSpec 时，遵循以下适配规则：

- 文件读取优先用 `rg`、`Get-Content` 等 shell 命令；文件修改优先用 `apply_patch`。
- 只有当前会话确实安装了对应 skill 时，才按 Codex skills 机制调用 `openspec-propose`、`openspec-archive-change` 或 `superpowers:*`；否则使用本文档中的 CLI 降级流程。
- Codex 默认不应静默执行网络安装或依赖下载。`npx @fission-ai/openspec ...`、依赖安装、远程访问等如遇网络限制，需要按 Codex 权限模型请求用户授权。
- 子代理只在用户明确要求或允许并行/子代理时使用；否则 apply 阶段使用 inline 模式。
- 自动 commit 是 HyperSpec 的流程纪律，但在 Codex 中应先确认用户接受该纪律；全程不自动 push。
- 需要项目画像时，优先运行本 skill 自带脚本：`python scripts/profiler.py --root <项目根目录> --write-state`。如需验证编译命令，再追加 `--verify-compile`。
- 需要判断阶段、断点或下一个可执行节点时，优先运行 DAG 状态计算：`python scripts/dag_status.py --root <项目根目录>`。该脚本读取 `hyperspec-dag.json` 和实际文件状态，输出 OpenSpec 风格的 JSON。

## 编排协议

HyperSpec 是**纯编排层**，只做以下五件事：

1. **项目感知** — 自动探测语言/框架/构建工具，生成 `project_profile` 驱动后续阶段的自适应行为
2. **需求发散与收敛** — 在需求模糊时先做 brainstorm，形成可进入规格阶段的收敛摘要
3. **状态检测** — 通过结构化状态文件 + 实际文件验证确定当前阶段和断点位置
4. **阶段路由** — 加载对应 prompt 文件，按其中的流程调用原生 skill
5. **Commit 纪律** — 每个 task/fix 完成后自动 commit，编译前置，不做 push

HyperSpec **不做**：

- 不手动创建 openspec artifacts（由 `openspec-propose` 负责）
- 不手动转 tasks → plan（由 `superpowers:writing-plans` 负责）
- 不手动执行归档操作（由 `openspec-archive-change` 负责）
- 不重申 TDD 规则（由 `superpowers:subagent-driven-development` 负责）
- 不重申审查规则（由 `superpowers:requesting-code-review` 负责）

### 各阶段委托的原生 Skill

| 阶段 | 委托 Skill | 职责 |
|------|-----------|------|
| brainstorm | `superpowers:brainstorming` 或 inline | 澄清问题空间、目标、非目标、约束、备选方案和推荐方向 |
| propose | `openspec-propose` | 通过 CLI 创建变更目录 + 生成所有 artifacts（proposal、design、specs、tasks） |
| propose | `superpowers:writing-plans` | 读取 openspec artifacts，生成 superpowers 格式实现计划 |
| apply | `superpowers:subagent-driven-development` 或 inline | 按计划执行实现，TDD + 子代理审查 |
| apply | `superpowers:verification-before-completion` | 全量验证 |
| apply | `superpowers:requesting-code-review` | 全局代码审查 |
| archive | `openspec-archive-change` | 通过 CLI 归档变更（含 spec sync） |

## 前提检查

触发后先检查两项：

**检查1：Superpowers** — 看 brainstorming 等 skill 是否可用。不可用则提示：`/plugin install superpowers@claude-plugins-official`

**检查2：OpenSpec** — 看项目根目录是否有 `openspec/`。没有则提示：`npx @fission-ai/openspec init`

注意：`openspec init` 除了创建 `openspec/` 目录外，还会在 `.claude/` 下生成配置文件和 slash commands。这些都是正常的副作用，不需要特别处理。

两项都通过后才继续。

## 项目分析器（Project Profiler）

前提检查通过后，**在首次运行或状态文件不存在时**，自动扫描项目生成 project_profile。Codex 运行时优先使用 `scripts/profiler.py` 完成扫描，结果保存到 `.hyperspec-state.yaml` 的 `project_profile` 字段。

推荐命令：

```bash
python <HyperSpec目录>/scripts/profiler.py --root <项目根目录> --write-state
```

如果用户允许验证编译环境，再运行：

```bash
python <HyperSpec目录>/scripts/profiler.py --root <项目根目录> --write-state --verify-compile
```

### 检测逻辑

| 检测项 | 检测方式 | 默认值 |
|--------|---------|--------|
| **languages** | 统计 `src/`、`lib/`、`app/` 等源码目录下的文件扩展名，取占比最高的 1-2 种 | `[]` |
| **frameworks** | 读取 `package.json` 的 dependencies/devDependencies、`pom.xml` 的 `<dependencies>`、`go.mod` 的 require 等提取关键框架名 | `[]` |
| **build_tool** | 检测根目录配置文件：`pom.xml` → maven，`build.gradle`/`build.gradle.kts` → gradle，`package.json` → npm/yarn/pnpm（看 lock 文件），`go.mod` → go，`Cargo.toml` → cargo，`pyproject.toml` → python | `unknown` |
| **compile_command** | 根据 build_tool 自动推导，见下方"构建命令映射" | `null` |
| **test_command** | 根据 build_tool + 测试目录推导，见下方"构建命令映射" | `null` |
| **structure** | 检查子目录模式：有 `modules/`/`packages/`/多个 `pom.xml`/`go.work` → `monorepo`；否则 → `single-module` | `single-module` |
| **has_ci** | 检查 `.github/workflows/`、`.gitlab-ci.yml`、`Jenkinsfile`、`azure-pipelines.yml` 等 | `false` |

### 构建命令映射

下表为默认推导值。项目分析器会在推导后执行**运行时验证**（见下方），根据实际环境校准命令。

| build_tool | compile_command（默认） | test_command（默认） |
|------------|----------------|--------------|
| maven | `mvn compile` | `mvn test` |
| gradle | `./gradlew compileJava` | `./gradlew test` |
| npm | `npm run build`（如果 script 存在） | `npm test`（如果 script 存在） |
| go | `go build ./...` | `go test ./...` |
| cargo | `cargo build` | `cargo test` |
| python | `null`（跳过编译） | `pytest`（如果安装了） |
| unknown | `null` | `null` |

### 命令运行时验证

默认推导完成后，按以下顺序验证（先检测参数，再执行验证）：

1. **项目特有参数检测**（在执行命令之前）：检查项目配置文件中是否有需要额外传入的参数：
   - Maven：检查根目录是否有 `settings.xml`，有则 compile_command 附加 `-gs ./settings.xml`
   - Gradle：检查是否有自定义 `gradle.properties` 或 `local.properties`
   - npm：检查 `.npmrc` 是否有 registry 配置
2. **执行编译命令**：运行调整后的 compile_command（如果非 null）
3. **成功**：确认命令可用，写入 project_profile
4. **失败且为环境问题**（JDK/Node 版本不匹配、依赖下载失败等）：**立即阻塞并报告**，等待用户确认正确的命令
5. **失败且为代码问题**（已有代码编译错误）：命令本身可用，写入 project_profile，编译错误留到 apply 阶段处理
6. **test_command**：不强制运行（可能依赖外部服务），但检查 test framework 是否安装（如 `which pytest`、检查 `package.json` 的 devDependencies）

### 项目 profile 的传递方式

project_profile 不会直接传给 openspec-propose 或 writing-plans（它们有自己的上下文读取机制），但 HyperSpec 在调用它们之前，会将 profile 信息作为**上下文前缀**拼接到 args 中：

- 调用 `openspec-propose` 时，在 description 前附加 `[项目: {languages} + {frameworks}, 构建: {build_tool}]`
- 调用 `writing-plans` 时，在 args 中附加 `项目技术栈: {languages} + {frameworks}，构建工具: {build_tool}，测试框架: {test_command}`
- apply 阶段使用 `compile_command` 和 `test_command` 驱动编译检查和验证

## 状态管理

### 状态文件：`.hyperspec-state.yaml`

位于项目根目录，HyperSpec 的**快速路由入口**。结构：

```yaml
version: 1
active_change: add-user-auth
phase: brainstorm | propose | apply | archive
checkpoint: profiler-done | brainstorm-started | brainstorm-done | requirements-confirmed | openspec-generated | plan-generated | plan-generated-and-confirmed | task-N-complete | verified | reviewed | apply-done | consistency-verified | archived | done
project_profile:
  languages: [java]
  frameworks: [spring-boot]
  build_tool: maven
  compile_command: mvn compile
  test_command: mvn test
  structure: single-module
  has_ci: true
```

### 安全策略：状态文件 vs 实际文件

状态文件用于快速路由（避免每次扫描所有目录），但在**关键节点**必须验证实际文件状态：

| 时机 | 验证内容 | 不一致处理 |
|------|---------|-----------|
| 阶段入口 | 状态文件声称的 phase 对应的文件是否存在 | 修正状态文件，路由到实际状态对应的阶段 |
| 断点恢复 | checkpoint 声称的进度是否与实际文件一致 | 回退到最近一个确认一致的状态 |
| 阶段出口 | 出口条件对应的实际文件是否满足 | 不满足则不退出，继续当前阶段 |

**原则**：实际文件状态是 ground truth，状态文件只是缓存。两者冲突时，以实际文件为准并修正状态文件。

## 状态检测

检查 `.hyperspec-state.yaml` 和实际文件状态，确定应该进入哪个阶段：

**Codex 优先做法：**

```bash
python <HyperSpec目录>/scripts/dag_status.py --root <项目根目录>
```

脚本输出 `nodes`、`next`、`missingDeps` 和文件证据。路由时优先选择 `next` 中的第一个节点；如果状态文件和 DAG 结果冲突，以 DAG 基于文件系统计算出的节点状态为准。需要可视化时运行：

```bash
python <HyperSpec目录>/scripts/dag_status.py --root <项目根目录> --format mermaid
```

### Step 1：读取状态文件

- 状态文件不存在 → 这是首次运行，执行项目分析器，然后根据用户需求清晰度进入 brainstorm 或 propose 阶段
- 状态文件存在 → 读取 phase 和 checkpoint

### Step 2：验证状态文件与实际文件一致性

根据状态文件中的 phase，验证对应的前提条件：

**phase = brainstorm 时验证：**
- `.hyperspec-brainstorm.md` 是否存在且非空？ → 存在则可恢复到 brainstorm 末尾，准备进入 propose
- 如果已有活跃变更目录或计划文件，说明实际进度已越过 brainstorm，按实际文件状态修正到 propose 或 apply
- 如果 checkpoint 为 `brainstorm-done` 但收敛摘要不存在或为空，回退到 `brainstorm-started`

**phase = propose 时验证：**
- `openspec/changes/` 下是否有活跃（非 archive）变更目录？ → 无则一致（propose 刚开始）
- **通用规则（适用于所有 checkpoint）**：如果有活跃变更目录且 `superpowers/plans/` 下有对应的计划文件（含 `<!-- hyperspec change: <active_change> -->`），说明实际进度已进入 apply 阶段，修正 `phase: apply`，根据 checkbox 状态判定 checkpoint
- 如果有活跃变更目录但无计划文件：根据变更目录下 artifacts 的完整程度判定 checkpoint（artifacts 完整 → `openspec-generated`，不完整 → `requirements-confirmed`）
- 如果 checkpoint ≥ `openspec-generated`：变更目录下的 artifacts 是否存在且非空？ → 有空文件则回退 checkpoint 到 `requirements-confirmed`

**phase = apply 时验证：**
- `superpowers/plans/` 下是否有包含 `<!-- hyperspec change: <active_change> -->` 的计划文件？ → 无则回退到 propose 阶段
- 计划文件中是否至少有 1 个 checkbox？ → 无则回退到 propose 阶段（plan 不完整）
- 如果 checkpoint 声称 `task-N-complete`：计划文件中对应的 checkbox 是否确实已勾选？ → 未勾选则回退到上一个确认一致的 checkpoint

**phase = archive 时验证：**
- 所有计划 checkbox 是否已勾选？ → 未全勾选则修正状态文件为 `phase: apply, checkpoint: reviewed`，路由到 apply
- 如果 checkpoint ≥ `consistency-verified`：`openspec/changes/archive/` 下是否有对应目录？ → 无则回退到 `consistency-verified`（重做归档）
- 如果 checkpoint ≥ `archived`：`openspec/changes/archive/` 下是否有对应目录？ → 无则回退到 `consistency-verified`（归档中断）
- **注意**：`.close-verification-done` 的存在性由 archive.md 内部处理（断点恢复表），SKILL.md 不据此覆盖 checkpoint，避免基于过期文件做错误路由

### Step 3：路由

| 状态文件 phase | 验证结果 | 路由到 |
|---------------|---------|--------|
| brainstorm | 一致 | brainstorm 阶段（从 checkpoint 恢复） |
| brainstorm | 已有规格/计划文件 | propose 或 apply 阶段（以实际文件为准） |
| propose | 一致 | propose 阶段（从 checkpoint 恢复） |
| propose | 不一致（artifacts 缺失） | propose 阶段（回退 checkpoint） |
| apply | 一致 | apply 阶段（从 checkpoint 恢复） |
| apply | plan 不存在或不完整 | propose 阶段 |
| archive | 一致 | archive 阶段（从 checkpoint 恢复） |
| archive | apply 未完成 | apply 阶段 |

### Step 4：无状态文件时的降级检测

如果状态文件不存在（可能是旧项目或手动删除），降级为文件扫描检测：

| 检查项 | 怎么查 | 结果 |
|--------|--------|------|
| 有 brainstorm 摘要？ | `.hyperspec-brainstorm.md` 是否存在且非空 | 有且无活跃变更 → propose 阶段（使用摘要作为输入） |
| 有活跃变更？ | `openspec/changes/` 下是否有非 archive 子目录 | 有 → 继续检查 |
| 有多个活跃变更？ | 活跃变更数量 > 1 | 是 → 让用户选择继续哪个 |
| 有计划文件？ | `superpowers/plans/` 下是否有与活跃变更对应的计划文件（文件含 `<!-- hyperspec change: <name> -->`） | 有 → 看实现状态 |
| 计划文件有效？ | 计划文件中是否至少有 1 个 checkbox | 无 → propose 阶段 |
| checkbox 状态？ | checkbox 全部未勾选 | → apply 阶段（全新执行） |
| checkbox 状态？ | checkbox 部分已勾选 | → apply 阶段（断点恢复） |
| checkbox 状态？ | checkbox 全部已勾选 | → apply 阶段（验证→审查→自动进入 archive） |

## 路由

根据检测结果，用 Read 工具加载对应文件并执行：

- **brainstorm 阶段** → 读取 skill 目录下的 `brainstorm.md`，按其中流程执行
- **propose 阶段** → 读取 skill 目录下的 `propose.md`，按其中流程执行
- **apply 阶段** → 读取 skill 目录下的 `apply.md`，按其中流程执行
- **archive 阶段** → 读取 skill 目录下的 `archive.md`，按其中流程执行

加载后严格按照文件中定义的流程、出口条件和硬门执行，不要跳步。

## 用户意图覆盖

如果用户明确指定了阶段（如「先头脑风暴」「先做规格」「直接开始实现」「归档收尾」），以用户意图为准，跳过状态检测直接加载对应文件。但如果前置条件不满足（如用户说「直接实现」但 `superpowers/plans/` 下没有计划文件），需要提醒用户先完成前置阶段。

## 状态文件更新时机

| 时机 | 更新内容 |
|------|---------|
| 项目分析器完成 | 写入 `project_profile`，需求模糊时 `phase: brainstorm`，需求明确时 `phase: propose`，`checkpoint: profiler-done` |
| brainstorm 开始 | `phase: brainstorm`，`checkpoint: brainstorm-started` |
| brainstorm 收敛完成 | 写入 `.hyperspec-brainstorm.md`，`phase: propose`，`checkpoint: brainstorm-done` |
| propose 阶段需求确认完成 | `checkpoint: requirements-confirmed`，`active_change: <变更名>` |
| openspec-propose 完成 | `checkpoint: openspec-generated` |
| writing-plans 完成 | `checkpoint: plan-generated` |
| propose 用户确认进入 apply | `phase: apply`，`checkpoint: plan-generated-and-confirmed` |
| apply 阶段每个 task 完成 | `checkpoint: task-N-complete` |
| apply 验证通过 | `checkpoint: verified` |
| apply 审查通过 | `checkpoint: reviewed` |
| apply 最终确认完成 | `phase: archive`，`checkpoint: apply-done` |
| archive 一致性验证通过 | `checkpoint: consistency-verified` |
| archive 归档完成 | `checkpoint: archived` |
| archive 全部完成 | 将 `.hyperspec-brainstorm.md` 移动到归档目录的 `brainstorm.md`（若存在），`checkpoint: done`，删除状态文件 |
