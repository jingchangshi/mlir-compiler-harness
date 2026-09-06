# Goal: Phase 20 — CompilerDev Harness Adapter Contract

`mlir-compiler-harness` 已完成 Phase 0–19：compiler graph、provenance、constraints、
findings、impact analysis、review memory 和 Python pipeline provenance。它是确定性的
compiler knowledge substrate，不是 Agent framework。

本阶段为外部 Agent workflow 定义稳定的消费接口：

- 在 `adapters/compiler-dev/` 记录 `mlir-repomap review`、`finding-impact`、
  `pipeline-stages`、`evidence` 的只读查询契约与任务预设序列；
- 定义独立 feedback artifact。feedback 是知识系统使用观察（例如 `review MergeVecScope`
  后仍需搜索 verifier location），不等同于 compiler design risk finding，绝不进入 graph；
- 在 Query API 中记录 CLI 消费面，并为 feedback schema 与文档一致性提供测试；
- 在 `docs/validation/phase20/` 留下 adapter design 与验证记录。

明确不做：Agent runtime、DeepSeek Harness 接入、外部 repo 修改、graph model 修改，以及
自动改变 finding 生命周期。

## CompilerDev Harness 的后续方向

不在 Codex 中一次性实现 external Harness。应在 dsh creative mode 用真实
AscendNPU-IR 任务逐步试验：任务开始时先理解仓库 context，再按类型查询 compiler memory
与 finding，最后才分析必要源码。bug/review 任务优先 `review`/`finding-impact`；架构或
lowering 任务优先 `pipeline-stages`。记录非敏感的 task、使用过的 query、是否手工搜索及
可能缺失的 knowledge，随后以重复的真实反馈反哺本仓库的 query/workflow 设计。
