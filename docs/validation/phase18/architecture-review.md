# 架构评审与缺口

## Q1–Q3

结论：Phase 0–17 在**单仓、证据驱动的分析/演进闭环**上完成了 “AI compiler
engineer memory system” 的初始目标；不是跨仓语义审阅的完整替代。证据为两仓 0
diagnostic 索引、pass/pipeline/review 查询、AV2/MVS 历史回放和两次 clean drift。
图仍仅存 fact/provenance/relation，review/finding reasoning 未写回图。

最有价值能力是 **finding evolution + review memory**：AV2-001 把 commit、实体、
guard diff 和 39 条 test 收敛为一个 review scope；MVS-001 让迁移后未受保护 contract
可重定位。最大限制是 Python/C++ hybrid flow 只有 construction provenance，缺少
可审计 Python stage graph；`pipeline make_ttgir` not found，而 composition 只返回
单 pass chain。

## 缺口分类

| 类别 | problem | evidence | impact | priority |
|---|---|---|---|---|
| A | 单仓 pass/finding/review 闭环满足 | 2 仓 0 diagnostic；2 个 replay 命中；7 个最新 drift clean | 无需开发 | 无 |
| B | `stale` 曾按 HEAD 脏状态而非 indexed snapshot 判定 | 刚索引的真实仓仍 stale | 无法判断查询新鲜度 | 已修复；高 |
| B | harness-side Triton review 需同时给 `--docs-dir` 和 `--dir` | 缺 `--dir` 时 finding 为空；两参数后得到 TTL-001 | 易误判 memory 为空 | 文档化；中 |
| C | Python composed flow 非 `pipeline` node | make_ttgir 查询 not found；composition 仅单-pass 链 | 无法审计 Python order/guard/contract | 高 |
| C | 跨仓 attribute/evidence 只报告 uncertainty | TTL-001 external evidence 不 drift-check | 无法给跨仓 contract verdict | 中；deferred |

## Q4：下一步

值得继续，但仅评估 **deeper semantic extraction**：它直接对应已观察到的 Python
stage order/guard 缺口。watchlist 只推送已有结果，MCP 不改变查询内容，clangd 无
wrong-fact 证据；均不优先。跨仓 contract validation 继续 deferred，本阶段未实现。
