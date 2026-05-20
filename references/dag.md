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

## 扩展原则

- 新增节点时先补 `hyperspec-dag.json`
- 再补 `scripts/dag_status.py` 的判定逻辑
- 最后再补 README / SKILL 说明
