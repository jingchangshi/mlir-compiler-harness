# Roadmap

已完成：Phase 0–19（ADR-001..024）。Phase 19 补齐 Python compiler orchestration 的
一等静态 pipeline provenance：Python AST stage order、binding→C++ builder 的唯一链、
显式不确定性，以及 `pipeline-stages` 查询。验证见 `docs/validation/phase19/`。

当前：维护确定性 graph、文档层 review/finding 和 evolution analysis。C++ compiler
facts、Python compiler orchestration、review memory、evolution analysis 已共同覆盖本
仓库的目标边界。

下一步建议：**stop / maintain**。先在真实 review 中收集 Python AST 的漏报或错误
事实证据，再重新评估后续工作；目前没有证据支持提前实施 watchlist、MCP、embedding、
clangd、runtime tracing、runtime contract graph 或 cross-repository validation。

仍记录的边界：Python runtime branch/动态 import/任意数据流不执行；跨仓 evidence
仍只报告 uncertainty；attribute value semantics 与完整 gtest coverage extraction 未实现。
这些都是有意边界，不应通过把 reasoning 写入 graph 或自动改变 finding status 来绕过。
