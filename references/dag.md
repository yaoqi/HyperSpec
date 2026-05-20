# HyperSpec DAG Reference

这是 HyperSpec 的 DAG 参考说明，和 `hyperspec-dag.json`、`scripts/dag_status.py` 配套使用。

## 目的

- 把 HyperSpec 的阶段路由显式化为节点和依赖
- 用文件系统证据计算节点状态
- 提供 `next` 作为主路由入口

## 节点类型

| 节点 | 含义 |
|------|------|
| `project-profile` | 项目画像完成 |
| `brainstorm` | 需求发散与收敛完成 |
| `openspec-artifacts` | OpenSpec artifacts 完成 |
| `implementation-plan` | 实现计划完成 |
| `implementation` | 代码实现完成 |
| `verification` | 全量验证完成 |
| `review` | 代码审查完成 |
| `consistency` | 规格一致性验证完成 |
| `archive` | 变更归档完成 |
| `cleanup` | 临时状态清理完成 |

## 状态值

| 状态 | 含义 |
|------|------|
| `done` | 文件证据或 checkpoint 已满足 |
| `ready` | 依赖已满足，可执行 |
| `blocked` | 仍缺少依赖 |

## 路由规则

1. 运行 `python scripts/dag_status.py --root <root>`
2. 读取 `next[0]`
3. 将 `next[0]` 映射到阶段文件
4. 若脚本不可用，则降级到 `SKILL.md` / `README.md` 中的旧规则

## 文件证据优先级

1. 实际文件状态
2. `hyperspec-dag.json`
3. `.hyperspec-state.yaml`

## 多变更状态

`.hyperspec-state.yaml` 支持按变更分区：

```yaml
active_change: add-user-auth
phase: apply
checkpoint: reviewed
changes:
  add-user-auth:
    phase: apply
    checkpoint: reviewed
  add-billing:
    phase: propose
    checkpoint: openspec-generated
```

`dag_status.py --change <name>` 会优先读取 `changes.<name>`，再回退到顶层 `phase/checkpoint`。顶层字段保留为默认变更和旧格式兼容入口。

## 文件职责与状态读写

| 文件 | 职责 | 状态读取 | 状态写入 |
|---|---|---|---|
| `SKILL.md` | 总调度规则 | 优先 `dag_status.py --change <name>`；降级时读 change-scoped state | 规定所有已确定变更名后的阶段推进都写 `changes.<active_change>` |
| `brainstorm.md` | 变更名前的需求发散 | 读顶层 checkpoint | 只写顶层 `phase/checkpoint`，因为此时通常还没有 change |
| `propose.md` | 锁定 change，生成规格和计划 | 先读 `changes.<active_change>.checkpoint`，无分区再回退顶层 | 需求确认时设置 `active_change`，并初始化/推进 `changes.<change>` |
| `apply.md` | 执行计划、验证、审查 | 先读 `changes.<active_change>.checkpoint`，无分区再回退顶层 | task、verified、reviewed、apply-done 都写 `changes.<active_change>` |
| `archive.md` | 一致性验证、归档、清理状态 | 先读 `changes.<active_change>.checkpoint`，无分区再回退顶层 | archived/done 写当前分区；最后删除当前分区，没其他变更才删状态文件 |
| `scripts/profiler.py` | 生成项目画像 | 不读状态 | `--active-change` 存在时初始化 `changes.<change>` |
| `scripts/dag_status.py` | DAG 状态计算 | `--change` 优先读 `changes.<change>`，再回退顶层 | 不写状态，只输出 `changeScoped` 和 DAG 节点 |
| `README.md` / `references/dag.md` | 使用说明 | 说明读取优先级 | 说明归档清理规则和多变更结构 |

最终状态文件语义：

```yaml
active_change: add-user-auth       # 默认当前变更
phase: apply                       # 旧格式兼容 / 默认缓存
checkpoint: reviewed               # 旧格式兼容 / 默认缓存

changes:
  add-user-auth:
    phase: apply
    checkpoint: reviewed
  add-billing:
    phase: propose
    checkpoint: openspec-generated
```

核心原则：

- 变更名前：允许只写顶层，比如 brainstorm。
- 变更名确定后：必须写 `changes.<active_change>`。
- 顶层 `phase/checkpoint` 只能作为默认缓存和旧格式兼容。
- 归档完成：删除当前 `changes.<active_change>`，不是无条件删除整个 `.hyperspec-state.yaml`。
- `dag_status.py` 的 `cleanup` 适配多变更规则：当前 change 分区不存在即可视为该 change 清理完成，即使其他 change 状态仍保留。

## 扩展原则

- 新增节点时先补 `hyperspec-dag.json`
- 再补 `scripts/dag_status.py` 的判定逻辑
- 最后再补 README / SKILL 说明
