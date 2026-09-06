# Roadmap

已完成：Phase 0–18（ADR-001..023）。Phase 18 在 AscendNPU-IR 与 triton-ascend 执行
真实索引、pass/pipeline 工作流、finding drift、impact、review memory 与历史 replay；
结论见 `docs/validation/phase18/`。

当前：维护已验证的确定性图、文档层 finding 和 review memory；不在图中保存推理、
review conclusion 或 finding status。

下一步仅作证据驱动的评估：

1. **Deeper semantic extraction（Python composed pipeline stage view）**：Phase 18
   证实 `pipeline-composition` 可解释单个 pass 的 Python→C++ provenance，却不能
   以 `pipeline` 查询完整 Python stage order、guard 和 swap contract。先验证一个
   通用表示能否覆盖两个目标仓，再决定是否实现。

仍 deferred：

- watchlist：Phase 18 最新提交检查均为 clean；没有推送机制的真实压力。
- MCP：CLI 已完成完整工作流，未观察到适配器阻塞。
- clangd：没有 wrong-fact incident；当前问题是 Python 编排语义而非 C++ 名称解析。
- runtime contract graph、embedding search、cross-repository contract validation：
  TTL-001 显示跨仓 evidence 仍需人工判断，但证据不足以承担该架构扩张。
- attribute value semantics、完整 gtest coverage extraction：维持既有限制记录。

已拒绝：把 finding/review reasoning 写入图、根据 drift 自动改变 finding status、以及
在没有真实工作流证据时提前启动新方向。
