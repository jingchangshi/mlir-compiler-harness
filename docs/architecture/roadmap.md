# Roadmap

已完成：Phase 0–20（ADR-001..024）。Phase 19 补齐 Python compiler orchestration 的
一等静态 pipeline provenance：Python AST stage order、binding→C++ builder 的唯一链、
显式不确定性，以及 `pipeline-stages` 查询。验证见 `docs/validation/phase19/`。

当前：维护确定性 graph、文档层 review/finding、evolution analysis 和外部消费契约。
Phase 20 为 CompilerDev Harness 固化了四个只读知识命令的使用边界及非敏感 feedback
schema；它不实现 Agent runtime，也不接入外部 Harness。

下一步建议：在 **dsh creative mode** 中以真实 Ascend compiler 任务试用
`adapters/compiler-dev/` 的预设序列，并仅收集非敏感 usage feedback。先验证 verifier
定位、finding impact 和 Python pipeline audit；只有重复、证据化的检索缺口才进入后续
query/workflow 设计。本仓库继续 **stop / maintain**，目前没有证据支持提前实施
watchlist、MCP、embedding、clangd、runtime tracing、runtime contract graph 或
cross-repository validation。

仍记录的边界：Python runtime branch/动态 import/任意数据流不执行；跨仓 evidence
仍只报告 uncertainty；attribute value semantics 与完整 gtest coverage extraction 未实现。
这些都是有意边界，不应通过把 reasoning 写入 graph 或自动改变 finding status 来绕过。
