# 仓库理解验证

两个真实仓均运行 `status`、`dialects`、`passes`、`pipelines`，索引诊断均为 0。

| 仓库 | dialect | pass | pipeline | pattern | constraint | test |
|---|---:|---:|---:|---:|---:|---:|
| AscendNPU-IR | 13 | 332 | 80 | 790 | 390 | 958 |
| triton-ascend | 8 | 144 | 8 | 190 | 53 | 187 |

Ascend 的查询直接给出 HFusion（46 op）和 HIVM（32 op）的 TableGen ownership，及
`Passes.td:719` MergeVecScope、`:154` AutoVectorizeV2、`:224` HFusion FlattenOps。
HFusion FlattenOps 的可用 pass 名是 `hfusion-flatten-ops`；错误的
`HFusionFlattenOps` 返回 not found，没有猜测。

triton 的 catalog 将 `triton-to-linalg` 定位到 `Passes.td:5`，C++ stage catalog
给出 15-stage `init_triton_ascend_passes_ttir`。因此四个导航查询可快速建立仓库
规模、dialect ownership 和 pass catalog；图中仅保留这些确定性事实及证据。
