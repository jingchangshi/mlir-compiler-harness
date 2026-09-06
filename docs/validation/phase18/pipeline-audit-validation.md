# Pipeline 审计验证

## AscendNPU-IR RegBase

对 `buildHFusionRegBasePipeline` 和 file-qualified
`HIVMRegbasePipelines.cpp:bufferizationPipeline` 运行 `pipeline --brief`、
`pipeline-builder`、`tests`、`changed`、`findings check`、`finding-impact`。

- `buildHFusionRegBasePipeline` 的 confirmed builder 是
  `HFusionRegbasePipelines.cpp:582`，caller 是 `PassPipeline.cpp:331`；guarded
  stage 1–4 以 `hfusion-flatten-ops` 结束。
- bufferization builder 在 `HIVMRegbasePipelines.cpp:223`。MergeVecScope 的两个
  mutually-exclusive guard 决定它在 bufferize 前或后执行；level 1 与 copy insertion
  交换会把新 copy 视为依赖，造成 no-op。MVS-001 补充了未 guard 的 single-use contract。
- `tests <file-qualified pipeline>` 返回空：这是没有发现 builder-name test，不是
  宣称没有端到端覆盖。4 条 merge-vf exact test 是可复现审查范围。

## triton-ascend hybrid flow

`init_triton_ascend_passes_ttir`（`triton_ascend.cc:62`）有 15 C++ stage；
triton-to-linalg 位于 annotation 后第 5 stage。生产 Python flow 是
`compiler.py:ttir_to_linalg`，composition query 可恢复 Python→binding→factory→pass。
当前 checkout 没有 `make_ttgir`：`pipeline`、`symbol`、`references make_ttgir` 都是
not found；这作为真实仓演进的负结果记录，没有用旧名称替代目标。

结论：C++ stage ownership、guard、lowering 邻接与历史风险可审计。Python provenance
可恢复，但 Python stage 不是一等 `pipeline` node，无法仅用 `pipeline` 输出完整
stage order/guard/swap contract；该限制仅记录为架构缺口。
