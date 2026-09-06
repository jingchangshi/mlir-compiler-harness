# CompilerDev Harness Adapter

这是一个面向 CompilerDev Harness 的**消费契约**，而不是 Agent runtime、提示词或外部
仓库集成。它把已有的 `mlir-repomap` 确定性知识查询暴露给任意可执行 shell 命令的
工作流消费者；图模型、finding 生命周期和现有 workflow 都不是本 adapter 的写入目标。

使用顺序与边界见：

- [查询契约](query-contract.md)：四个可依赖的知识命令及其不确定性规则；
- [工作流契约](workflow-contract.md)：按任务选择查询的只读序列；
- [反馈工件](feedback-schema.md)：记录知识系统使用观察，**不等同于 finding**；
- [演进方向](direction.md)：仅为未来 dsh creative mode 的方向，不实现外部 Harness。

前置条件是目标 compiler repo 已完成 `mlir-repomap index --full`，且调用方在目标 repo
中运行查询（或显式传递全局 `--repo`）。每次会话先读 `status` 的 `index.stale`：为
`true` 时先刷新索引，再把结果用于工程推理。

本目录遵守 adapter 薄层原则（ADR-010）：不复制 `docs/workflows/` 的方法论，不引入
模型、MCP、DeepSeek Harness 依赖，也不修改 `repomap/` 的 compiler graph。
