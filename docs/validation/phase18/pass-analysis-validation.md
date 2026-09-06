# Pass 分析工作流验证

按 `pass-analysis` 工作流运行 `pass`、`review`、`findings list/show`、
`pass-intent`、`pass-constraints`、`pipeline-builder`、`attribute-provenance`，并只
读取证据指向的源码和既有 dossier。以下“工程师解释”不写入图。

## AscendNPU-IR

| pass | Intent（图事实） | invariant / constraint | history / risk |
|---|---|---|---|
| MergeVecScope (`hfusion-merge-vf`) | `Passes.td:719`：“Merge vf function”；heuristic optimization | RegBase bufferization 中 level 1/2 两处、guard 为 `enableVfMergeLevel == 1/2`；`MergeVecScope.cpp:1422/:1625` 为两个 `mergedFunc.verify` legality guard | `review` 返回 MVS-001/MVS-002；single-use VF 未被 guard 覆盖；4 条 exact lit test |
| AutoVectorizeV2 | `Passes.td:154`：“Tile, fuse and vectorize all linalg named ops” | 位于 `vf-fusion` 与 `outline-vector-function` 之间，guard `enableAutoVectorizeV2`；1 个 legality guard | AV2-001 记录 verifier-completeness meta-contract；39 条 exact lit test |
| HFusion FlattenOps | `Passes.td:224`：“Flatten linalg and hfusion ops”；inferred in-place rewrite | RegBase flatten family 第 4 stage，guard `options.enableFlatten`；2 个 legality guard、10 tests | 下游 flatten→decompose contract 的 swap outcome 是可能 silent wrong lowering |

工程师解释：MergeVecScope 合并 VF 以降低调用/调度开销，guard 保护合并结果而非
call-count；AV2 的提交应优先审查 clone-plan-verify acceptance path；FlattenOps 为
后续 RegBase lowering 规范化 shape。

## triton-ascend：`triton-to-linalg`

`pass` 连接 `Passes.td:5`、`createTritonToLinalgPass`、46 条 exact lit test 和两条
confirmed pattern-populator 链（`TritonToLinalgPass.cpp:1334/:1407`）。图标为 inferred
lowering boundary；`pipeline-composition` 给出 `compiler.py:ttir_to_linalg` →
`add_triton_to_linalg`（`triton_ascend.cc:84`）→ factory → pass。将 harness-side
`--docs-dir` 与 `--dir` 同时传给 `review` 后得到 1 条 review record 和 TTL-001。
TTL-001 也诚实报告 `StrideAlignDimsAttr` 在本仓不存在，不能伪装为本仓 provenance。

结论：Intent、invariant、constraint、history、risk 和精确 tests 均能由查询与少量
evidence 回答；unguarded invariant 是 review/finding 层结论，三层边界保持成立。
