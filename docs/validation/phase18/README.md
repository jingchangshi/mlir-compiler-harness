# Phase 18：真实仓库演进验证

日期：2026-09-06。目标是验证 Phase 0–17 是否支撑真实 compiler engineer 工作流，
不是扩展图模型。

| 仓库 | HEAD | 范围 |
|---|---|---|
| AscendNPU-IR | `5671889a3` | MergeVecScope、AutoVectorizeV2、HFusion FlattenOps、RegBase |
| triton-ascend | `8ba4ac4ce` | triton-to-linalg、C++/Python hybrid pipeline |

两个仓在验证前已有未提交内容；未修改其编译器源。索引分别扫描 2,951 与 1,265
文件，均为 0 diagnostic。修复 `status.stale` 后重新索引均为 `stale=false`，故
查询基于实际工作树快照。控制台入口未预装，以下 `mlir-repomap` 使用等价模块入口
`PYTHONPATH=repomap/src python3 -m mlir_repomap.cli` 执行。

- [仓库理解](repository-understanding.md)
- [Pass 工作流](pass-analysis-validation.md)
- [Pipeline 审计](pipeline-audit-validation.md)
- [历史回归回放](regression-replay.md)
- [新提交漂移](drift-validation.md)
- [新工程师可用性](agent-usability.md)
- [架构评审与缺口](architecture-review.md)

结论：单仓的确定性图、finding 漂移与 review memory 已形成可用闭环；跨仓语义与
Python pipeline 完整 stage 视图仍有限制。没有引入 watchlist、MCP、embedding、
clangd、runtime contract graph 或跨仓 contract validation。
