# HyperSpec:brainstorm — 头脑风暴前置阶段

## 目标

在进入 OpenSpec propose 前，把模糊想法澄清成可写规格的收敛输入。brainstorm 只做发散、比较和收敛，不创建 OpenSpec artifacts，不写实现代码，不创建分支。

## 进入条件

进入本阶段的典型情况：

- 用户明确说「先头脑风暴」「先聊方案」「帮我梳理一下」「还不确定怎么做」
- 需求目标、用户、边界、成功标准或约束不清晰
- 方案空间较大，存在多个技术路线或产品路线

跳过本阶段的典型情况：

- 用户需求已经明确，并要求「直接做规格」或「完整流程开发」
- 已存在 `.hyperspec-brainstorm.md` 且内容仍适用
- 已有活跃 OpenSpec change 或实现计划，说明流程已经进入后续阶段

## 阶段流程

### 1. 建立讨论边界

读取 `project_profile` 和用户原始需求，先判断是否真的需要 brainstorm。若需求已经足够清晰，说明将跳过 brainstorm 并进入 propose。

需要 brainstorm 时，更新 `.hyperspec-state.yaml`：

```yaml
phase: brainstorm
checkpoint: brainstorm-started
```

### 2. 调用 brainstorming 或 inline 执行

优先使用可用的 `superpowers:brainstorming` skill。若当前会话没有该 skill，则 inline 执行同等流程。

brainstorm 必须覆盖：

- **Problem**：要解决的问题和触发背景
- **Users**：主要使用者、受影响角色、调用方
- **Goals**：本次要达成的结果
- **Non-goals**：明确不做什么
- **Constraints**：技术、时间、兼容性、安全、性能、数据、部署约束
- **Options**：可选方案及取舍
- **Recommendation**：推荐方向和理由
- **Open questions**：仍未确认但会影响规格的问题
- **Success criteria**：进入 propose 时可检验的成功标准

交互规则：

- 一次只问一个关键问题。
- 如果用户要求自主推进，基于现有上下文做合理假设，并在输出里标明假设。
- 不为追求完整而无限追问；当剩余问题不阻塞 propose 时，记录为 open questions。

### 3. 生成收敛摘要

将结果写入项目根目录的 `.hyperspec-brainstorm.md`，作为 propose 的输入前缀。推荐结构：

```markdown
# HyperSpec Brainstorm

## Original Request

## Problem

## Goals

## Non-goals

## Constraints

## Options Considered

## Recommended Direction

## Open Questions

## Success Criteria
```

完成后更新 `.hyperspec-state.yaml`：

```yaml
phase: propose
checkpoint: brainstorm-done
```

### 4. 交给 propose

读取 `propose.md` 并继续。调用 `openspec-propose` 时，把 `.hyperspec-brainstorm.md` 的收敛摘要作为需求描述的一部分，位于 `project_profile` 上下文前缀之后、用户原始需求之前或之后均可，但必须让 OpenSpec 看到推荐方向、非目标和成功标准。

## 出口条件

- `.hyperspec-brainstorm.md` 存在且非空
- 至少包含 Problem、Goals、Non-goals、Recommended Direction、Success Criteria
- `.hyperspec-state.yaml` 已更新为 `phase: propose, checkpoint: brainstorm-done`

## 断点恢复

| checkpoint | 实际文件状态 | 恢复到 |
|-----------|-------------|--------|
| `profiler-done` | `.hyperspec-brainstorm.md` 不存在 | Step 1 |
| `brainstorm-started` | `.hyperspec-brainstorm.md` 不存在或为空 | Step 2 |
| `brainstorm-started` | `.hyperspec-brainstorm.md` 存在且非空 | Step 3，检查质量后进入 propose |
| `brainstorm-done` | `.hyperspec-brainstorm.md` 存在且非空 | propose 阶段 |
| `brainstorm-done` | `.hyperspec-brainstorm.md` 不存在或为空 | 回退到 `brainstorm-started` |

## 硬门

本阶段禁止创建或修改 `openspec/changes/` 下的 artifacts，禁止写实现代码，禁止创建分支。任何实现行为必须等到 apply 阶段。
