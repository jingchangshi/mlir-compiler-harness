# Roadmap

已完成：Phase 0–21（ADR-001..025）。Phase 21 在不改变 compiler graph、finding 生命周期或
SQLite index 的前提下，将 CompilerDev feedback contract 扩展为 v2：既保留已提交 v1 工件，
也能以去敏的 route、usage 和 operational 观察表达 `adoption-missed`。

当前：维护确定性 graph、文档层 review/finding、evolution analysis，以及只读外部消费契约。
feedback 是知识系统使用观察，不是 compiler fact；自动或 Agent 生成的记录只是 candidate，必须经
人工审核并标为 curated 后才可作为 architecture evolution evidence。

下一阶段：**CompilerDev Production Knowledge Observation Loop**。在 consumer repo 的真实
CompilerDev 会话中，按任务类型执行既有查询序列，记录最小、非敏感的 v2 candidate feedback，审核
后形成 curated evidence。重点衡量正确 skip 与 adoption-missed、查询充分性、索引刷新/截断等运行
信号；只有重复且经过人工审查的缺口才可提出新的确定性 query 或 workflow 变更。本仓不实现 Agent
runtime，也不采集或持有 session/raw telemetry。

仍记录、但不在本 Phase 实施的候选：

- Python Pipeline Provenance Hardening；
- Attribute Value Provenance。

继续明确不提前实施：watchlist、MCP、clangd、embedding、runtime tracing、Test Coverage Extraction、
cross-repository validation 或任何将 reasoning/session telemetry 写入 graph 的机制。Python runtime
branch、动态 import、任意数据流不执行；跨仓 evidence 仍只报告 uncertainty。
