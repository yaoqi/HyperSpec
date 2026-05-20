# HyperSpec

规格驱动 + 工程纪律的完整开发工作流 Skill，协调 [OpenSpec](https://github.com/fission-ai/openspec)（规格管理）和 [Superpowers](https://github.com/obra/superpowers)（brainstorming + TDD + 子代理审查），从想法澄清到规格、实现、归档一条流程走完。

OpenSpec 管「做什么和为什么」，Superpowers 管「怎么做和做得对不对」。HyperSpec 是**纯编排层**，只做项目感知、状态检测、阶段路由、commit 纪律，不重写任何原生 skill 的功能。

## 核心价值

- **项目感知**：自动探测语言/框架/构建工具，自适应生成规格和执行策略
- **头脑风暴前置**：需求模糊时先发散和收敛，再进入规格阶段
- **需求先行**：强制先产出规格文档再写代码，避免 AI 闷头实现方向跑偏
- **纯编排层**：不重写 OpenSpec/Superpowers 功能，只做调用和衔接
- **断点恢复**：结构化状态文件 + 实际文件双重验证，任何中断点可精确恢复
- **智能执行**：根据任务数量、依赖关系、跨模块性等多因子选择最优执行模式
- **多语言支持**：自动适配 Java/Node/Go/Rust/Python 等不同技术栈的编译和测试命令

## 前置依赖

| 依赖 | 用途 | 检查方式 | 安装方式 |
|------|------|----------|----------|
| **Superpowers** skill | TDD、计划编写、子代理开发、代码审查 | 检查 brainstorming 等 skill 是否可用 | `/plugin install superpowers@claude-plugins-official` |
| **OpenSpec** CLI | 规格文档管理（变更提案、设计文档、任务拆分、归档） | 检查项目根目录是否有 `openspec/` | `npx @fission-ai/openspec init` |

## 安装

将 HyperSpec skill clone或下载到本地：

```bash
# 克隆仓库
git clone https://github.com/wind7rui/HyperSpec hyperspec
```

**Claude Code**安装：

```bash
cp -r hyperspec ~/.claude/skills/hyperspec
```

**Cursor**安装：

```bash
cp -r hyperspec .cursor/skills/hyperspec
```

**Codex CLI**安装：

```bash
cp -r hyperspec ~/.codex/skills/hyperspec
```

## Codex 适配

HyperSpec 在 Codex 中按同一套“头脑风暴前置 + 三阶段交付”流程运行，但执行动作需要映射到 Codex 的本地工具：

| 原文动作 | Codex 中的做法 |
|---------|---------------|
| 读取文件 | 使用 shell 的 `Get-Content`/`rg`，或直接按 Codex skill 规则读取 |
| 写/改文件 | 手工小改使用 `apply_patch`；格式化、批量机械改写可用项目自带工具 |
| 调用原生 skill | 如果 Codex 当前会话有对应 skill，按 Codex skills 规则加载；没有则按文档中的 CLI 降级方案执行 |
| AskUserQuestion | 在 Default 模式下尽量自主判断；必须确认时用简短自然语言提问 |
| 子代理实现/审查 | 只有用户明确允许并行/子代理时使用 Codex sub-agent；否则使用 inline 模式 |
| 运行网络命令 | 如 `npx`、依赖安装、远程访问失败，需要按 Codex 权限模型请求升级 |
| 自动 commit | 仅在用户要求或明确接受 HyperSpec 自动提交纪律时执行；默认不 push |

Codex 版新增了一个无第三方依赖的项目分析脚本：

```bash
python scripts/profiler.py --root /path/to/project
python scripts/profiler.py --root /path/to/project --write-state
python scripts/profiler.py --root /path/to/project --write-state --verify-compile
```

默认只输出 JSON，不修改项目。加 `--write-state` 后会在目标项目根目录生成 `.hyperspec-state.yaml`。加 `--verify-compile` 后会实际运行推导出的编译命令；如果该命令需要下载依赖或访问网络，Codex 需要先获得用户授权。

## 使用方式

在 Claude Code / Cursor / Codex 对话中输入：

```
用hyperspec开发一个用户认证功能
```

或更自然地表达：

```
规格驱动开发：给订单模块加上导出Excel功能
完整流程开发一个定时任务，每天凌晨同步数据
```

skill 会自动检测项目状态，判断应进入哪个阶段。你也可以显式指定阶段：

- `先头脑风暴` → 强制进入 brainstorm 阶段
- `先做规格` → 强制进入 propose 阶段
- `直接开始实现` → 跳到 apply 阶段（需已有实现计划）
- `归档收尾` → 进入 archive 阶段

## 编排协议

HyperSpec 是**纯编排层**，只做以下四件事：

1. **项目感知** — 自动探测语言/框架/构建工具，生成 `project_profile` 驱动后续阶段的自适应行为
2. **状态检测** — 通过结构化状态文件（`.hyperspec-state.yaml`）+ 实际文件验证确定当前阶段和断点位置
3. **阶段路由** — 加载对应 prompt 文件，按其中的流程调用原生 skill
4. **Commit 纪律** — 每个 task/fix 完成后自动 commit，编译前置，不做 push

HyperSpec **不做**：

- 不手动创建 openspec artifacts（由 `openspec-propose` 负责）
- 不手动转 tasks → plan（由 `superpowers:writing-plans` 负责）
- 不手动执行归档操作（由 `openspec-archive-change` 负责）
- 不重申 TDD 规则（由 `superpowers:subagent-driven-development` 负责）
- 不重申审查规则（由 `superpowers:requesting-code-review` 负责）

## 工作流概览

HyperSpec 将一次完整的开发周期分为一个可选前置阶段和三个交付阶段，每个阶段委托给原生 skill 或 inline 流程执行：

```
+======================+     +==================+     +================+     +================+
| brainstorm（可选）    | --> | propose（规格）   | --> | apply（实现）    | --> | archive（归档） |
| 问题澄清              |     | 项目分析          |     | TDD 实现        |     | 一致性验证       |
| 方案发散              |     | 需求确认          |     | verification   |     | archive-change  |
| 方向收敛              |     | openspec-propose |     | code-review    |     | specs 合并      |
| 禁止写规格/代码        |     | writing-plans    |     | 禁止改规格       |     |                |
+======================+     +==================+     +================+     +================+
```

**各阶段委托的原生 Skill：**

| 阶段 | 委托 Skill | 职责 |
|------|-----------|------|
| brainstorm | `superpowers:brainstorming` 或 inline | 澄清问题空间、目标、非目标、约束、备选方案和推荐方向 |
| propose | `openspec-propose` | 通过 CLI 创建变更目录 + 生成所有 artifacts |
| propose | `superpowers:writing-plans` | 读取 openspec artifacts，生成实现计划 |
| apply | `superpowers:subagent-driven-development` 或 inline | 按计划执行实现 |
| apply | `superpowers:verification-before-completion` | 全量验证 |
| apply | `superpowers:requesting-code-review` | 全局代码审查 |
| archive | `openspec-archive-change` | 通过 CLI 归档变更 |

**各阶段产出：**

| 阶段 | 产出 |
|------|------|
| brainstorm | `.hyperspec-brainstorm.md` 收敛摘要，archive 后移动为归档目录的 `brainstorm.md` |
| propose | `proposal.md` / `design.md` / `specs/` / `tasks.md` + `superpowers/plans/` 下的实现计划 |
| apply | 可执行代码 / 编译通过 / 审查通过 |
| archive | 归档记录 / specs 合并到主规格库 |

## 阶段详解

### brainstorm 阶段 — 把模糊想法收敛成规格输入

当用户需求还不清晰，或存在多个产品/技术方向时，HyperSpec 会先进入 brainstorm 阶段。此阶段只做问题澄清、方案发散、取舍比较和推荐方向收敛。**本阶段禁止写规格、写代码或创建分支。**

**产出文件：**

| 文件 | 内容 |
|------|------|
| `.hyperspec-brainstorm.md` | 原始需求、问题定义、目标、非目标、约束、备选方案、推荐方向、开放问题、成功标准 |

如果用户需求已经明确，或用户说「直接做规格」，此阶段可以跳过。

### propose 阶段 — 把模糊想法变成可执行任务

将用户需求从模糊描述转化为完整的规格文档和实现计划。**本阶段禁止写任何代码或创建分支。**

**步骤：**

1. **项目分析** — 自动探测语言、框架、构建工具、测试框架，生成 project_profile
2. **需求确认** — 与用户交互确认需求（HyperSpec 自身逻辑，不委托）
3. **调用 openspec-propose** — 通过 CLI 创建变更目录，按依赖顺序生成 proposal → design → specs → tasks
4. **调用 writing-plans** — 读取 openspec artifacts + project_profile，生成适配技术栈的实现计划
5. **用户确认** — 展示产出摘要，请用户确认进入 apply

**产出文件：**

| 文件 | 生成者 | 内容 |
|------|--------|------|
| `proposal.md` | openspec-propose | 变更提案 — 背景、目标、影响范围 |
| `design.md` | openspec-propose | 技术方案 — 架构、选型、决策 |
| `specs/` | openspec-propose | 规格增量 — ADDED/MODIFIED/REMOVED |
| `tasks.md` | openspec-propose | 任务清单 — 按依赖排序 |
| `superpowers/plans/*.md` | writing-plans | 实现计划 — 带 checkbox 的微步骤 |

### apply 阶段 — 用工程纪律实现规格

按 propose 阶段生成的实现计划执行开发。

**智能执行模式选择：**

HyperSpec 根据多因子分析选择最优执行模式：

| 因子 | 完整模式倾向 | 轻量模式倾向 |
|------|-------------|-------------|
| 任务数量 | ≥ 6 | ≤ 5 |
| 跨模块性 | ≥ 3 个模块 | 1-2 个模块 |
| 项目结构 | monorepo | single-module |

| 模式 | 方式 |
|------|------|
| 完整模式 | 调用 `subagent-driven-development`，子代理实现+审查 |
| 轻量模式 | 当前会话直接执行 |

**提交纪律：** 每个 task 完成后：编译检查 → 更新计划 checkbox → 更新状态文件 → commit。全程不做 push。

**流程：**
1. 执行实现（逐 Task 或子代理派发）
2. 调用 `verification-before-completion` 全量验证
3. 调用 `requesting-code-review` 全局审查
4. 修复审查问题后重新验证，循环直到通过

**硬门：** 本阶段禁止修改 `openspec/changes/` 下的规格文档。

### archive 阶段 — 验证一致、归档收尾

验证代码实现和规格文档的一致性，归档变更，完成开发周期。

**步骤：**

1. **规格一致性验证** — 逐项检查 design/specs/tasks 是否在代码中体现，生成验证清单
2. **处理不一致** — 改代码或改规格，重新验证直到通过
3. **调用 openspec-archive-change** — 通过 CLI 归档变更（含 artifact 完成、task 完成检查）
4. **归档 brainstorm 摘要** — 将根目录 `.hyperspec-brainstorm.md` 移动到归档目录的 `brainstorm.md`（如存在）
5. **分支收尾 + 总结** — 提交剩余文件，展示变更摘要

## 状态管理与断点恢复

### 结构化状态文件

HyperSpec 使用 `.hyperspec-state.yaml` 跟踪当前进度：

```yaml
version: 1
active_change: add-user-auth
phase: apply
checkpoint: task-3-complete
project_profile:
  languages: [java]
  frameworks: [spring-boot]
  build_tool: maven
  compile_command: mvn compile -q
  test_command: mvn test
  structure: single-module
  has_ci: true
```

**安全策略**：状态文件用于快速路由，但在关键节点验证实际文件状态。两者冲突时以实际文件为准。

### 自动状态检测

重新运行 `/hyperspec` 时，skill 会自动检查状态文件和实际项目文件状态：

| 项目状态 | 进入阶段 |
|----------|----------|
| 无状态文件 + 需求模糊 + 无活跃变更 | brainstorm 阶段（首次运行） |
| 无状态文件 + 需求明确 + 无活跃变更 | propose 阶段（首次运行） |
| 有 `.hyperspec-brainstorm.md` 但无活跃变更 | propose 阶段（使用 brainstorm 摘要作为输入） |
| 有活跃变更但无计划文件 | propose 阶段（补生成计划） |
| 有计划文件但无 checkbox（plan 不完整） | propose 阶段（回到计划生成） |
| 有计划文件但未开始（无已勾选 checkbox） | apply 阶段（全新执行） |
| 有计划文件且部分 checkbox 勾选 | apply 阶段（断点恢复） |
| 有计划文件且全部 checkbox 勾选 | apply 阶段（验证→审查→自动进入 archive） |
| 有多个活跃变更 | 让用户选择 |

### 各阶段断点恢复

- **brainstorm 阶段：** 通过 checkpoint 和 `.hyperspec-brainstorm.md` 恢复到发散或收敛完成状态
- **propose 阶段：** 通过 checkpoint 精确恢复到需求确认、openspec 生成、计划生成等具体步骤
- **apply 阶段：** 通过 checkpoint 精确恢复到具体 task，状态文件和 checkbox 双重验证
- **archive 阶段：** 通过 checkpoint 恢复到验证、归档、分支收尾等具体步骤

## 项目分析器

HyperSpec 首次运行时自动探测项目特征：

| 检测项 | 检测方式 | 影响 |
|--------|---------|------|
| 语言 | 源文件扩展名统计 | plan 生成、build 命令 |
| 框架 | 依赖配置文件 | spec 设计方案风格 |
| 构建工具 | 根目录配置文件名 | 编译/测试命令自动选择 |
| 测试框架 | 测试目录结构 + 依赖 | TDD 步骤中的具体工具 |
| 项目结构 | 子目录模式 | 执行模式选择 |
| CI 配置 | CI 配置文件是否存在 | 验证策略 |

**支持的构建工具自动检测：**

| 配置文件 | compile_command | test_command |
|----------|----------------|--------------|
| `pom.xml` | `mvn compile -q` | `mvn test` |
| `build.gradle` | `./gradlew compileJava` | `./gradlew test` |
| `package.json` | `npm run build` | `npm test` |
| `go.mod` | `go build ./...` | `go test ./...` |
| `Cargo.toml` | `cargo build` | `cargo test` |
| `pyproject.toml` | 跳过 | `pytest` |

## 产出的目录结构

一次完整的 HyperSpec 运行后，项目目录结构如下：

```
项目根目录/
├── .hyperspec-state.yaml           # 运行期间存在，完成后删除
├── .hyperspec-brainstorm.md        # 运行期间可选存在，archive 后移动到归档目录
├── openspec/
│   ├── specs/                      # 主规格库（archive阶段合并）
│   │   └── user-auth/
│   │       └── spec.md
│   └── changes/
│       └── archive/                # 已归档变更
│           └── 2026-05-14-add-user-auth/
│               ├── .openspec.yaml
│               ├── proposal.md
│               ├── brainstorm.md
│               ├── design.md
│               ├── tasks.md
│               └── specs/
│                   └── user-auth/
│                       └── spec.md
└── superpowers/
    └── plans/
        └── 2026-05-14-add-user-auth.md  # 实现计划（带checkbox）
```

## 设计原则

- **纯编排层：** HyperSpec 只做项目感知、状态检测、阶段路由、commit 纪律，不重写任何原生 skill 的功能
- **先发散再收敛：** 模糊需求先进入 brainstorm，明确需求可直接进入 propose
- **规格与实现分离：** propose 阶段只产出文档，apply 阶段只写代码，各自有硬门禁止越界
- **项目感知自适应：** 根据项目技术栈自动调整编译命令、测试策略、执行模式
- **每个阶段有明确出口条件：** 不满足出口条件就不能进入下一阶段
- **可中断、可恢复：** 结构化状态文件 + 实际文件双重验证，支持从任何断点精确恢复
- **用户意图优先：** 自动检测只是默认行为，用户显式指定阶段时以用户意图为准
- **实际文件为 ground truth：** 状态文件是缓存，实际文件状态是权威，冲突时以实际文件为准

## 常见问题

### 可以跳过某个阶段吗？

可以。用显式指令指定阶段，如「直接开始实现」。但前置条件必须满足（比如 apply 阶段需要有实现计划），否则 skill 会提示你先完成前置阶段。

### 如果实现过程中发现规格设计有问题怎么办？

apply 阶段的硬门禁止修改规格文档。你可以记录问题继续实现，等进入 archive 阶段后统一处理不一致。如果问题严重影响实现，可以主动回到 propose 阶段重新设计。

### 支持哪些编程语言和项目类型？

不限制语言和项目类型。HyperSpec 会自动探测项目技术栈并自适应调整编译/测试命令和执行策略。Java/Maven、Java/Gradle、Node.js、Go、Rust、Python 等主流技术栈都有内置支持。
