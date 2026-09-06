# 新提交漂移验证

| 仓库 | 检查区间 | `findings check` | `finding-impact` |
|---|---|---|---|
| AscendNPU-IR | `ac3d07dcd..5671889a3` | 5 findings，0 needs review、5 clean、6 个 snippet 可验证 | AV2-001 无 impact signal，是明确 negative result |
| triton-ascend | `62f9f86fd..8ba4ac4ce` | 2 findings，0 needs review、2 clean、3 个 snippet 可验证 | TTL-001 本仓无 signal；保留 external evidence/attribute uncertainty |

没有出现“任何最近 commit 都产生 review”的 false positive。此两次 clean 不能证明没有
所有 false negative；真实 `fa682a1a3`/`4ddead06f` replay 的准确命中提供了更强的
反向证据。TTL-001 的 AscendNPU-IR evidence 明确标为 external、单仓不 drift-check，
不是错误的跨仓结论。
