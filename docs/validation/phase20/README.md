# Phase 20：CompilerDev Harness Adapter Contract

Phase 20 只定义外部 CompilerDev 工作流如何消费现有知识系统，不实现 Agent runtime、
不接入 DeepSeek Harness，且不修改 compiler graph model。

交付物在 `adapters/compiler-dev/`：四个已存在的 CLI 入口（`review`、
`finding-impact`、`pipeline-stages`、`evidence`）的稳定消费契约、任务预设查询序列、以及
独立的 feedback schema。feedback 明确是使用观察：例如对 `MergeVecScope` 执行 `review`
后仍需手工寻找 verifier，可提出“缺少 verifier location query”的候选缺口；这不是
compiler design risk，不创建 finding，不写 graph。

验证覆盖：

```bash
PYTHONPATH=repomap/src python3 -m pytest -q
PYTHONPATH=repomap/src python3 -m mlir_repomap.cli --help
```

新增单元测试验证 feedback 的有效样例、非法查询命令、敏感内容标记和文档所列命令与实际
CLI parser 的一致性，并确认 `review` 同样保留 stable `index` envelope。对本地既有
AscendNPU-IR / triton-ascend 索引的只读抽查中，`review MergeVecScope` 返回 2 个关联
finding，`finding-impact MVS-001` 给出 hfusion-merge-vf 的建议审查范围，
`pipeline-stages ttir_to_linalg` 返回 15 个 stage 和 1 条未解析 binding diagnostic。
`evidence pass:hfusion-merge-vf` 在抽查时报告 `index.stale=true`，因此其空 evidence
不被当作结论；这正是 consumer 必须先检查 envelope 的原因。该阶段没有外部 Harness
运行记录；未来应在 dsh creative mode 用真实 Ascend compiler 任务收集非敏感反馈后再决定
是否扩展查询面。
