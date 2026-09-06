# 历史回归回放

## AV2：`fa682a1a3`

`finding-impact AV2-001 --since fa682a1a3^` 精确解析
`pass:hfusion-auto-vectorize-v2`，得到 `AutoVectorizeV2.cpp` 的 1 个 file-commit
signal 和 `possible strengthening (guard(s) added)` constraint diff；review scope 是
1 个 legality guard 与 39 条链接测试，且无 uncertainty。`git show --stat` 证实该
提交为 “enable MCF by default and drop AutoVectorizeV2 retry/fallback”，确实修改该
源文件和测试。因此系统定位 AV2-001 但不自动改变其 status。

## MergeVecScope：`4ddead06f`

`finding-impact MVS-001 --since 4ddead06f^` 精确解析
`pass:hfusion-merge-vf`，得到 4 个 evidence-file commits，constraint diff 为
`no baseline content (file absent at base ref)`。`git show --stat` 证实该真实提交是
“migrate MergeVecScope from A5”，首次加入 `MergeVecScope.cpp` 和四个 MLIR tests。
系统将“文件在基线前不存在”保留为负结果，而不是误报 guard weakening。

两个 before/after replay 都命中预期 finding，并把审查收敛到实体、guard 和测试。
