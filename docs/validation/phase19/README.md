# Phase 19：Python Pipeline Semantic Provenance

本阶段把 AST 可证实的 Python 编排提升为一等 `pipeline`，不执行 Python、不进行
LLM 推断，也不把 review reasoning 写入图。

实现模型：

```text
Python pipeline --PIPELINE_COMPOSED_BY--> Python function
       |
       +--PIPELINE_CONTAINS(order, file:line)--> resolved pass / explicit marker
       |
       +--PIPELINE_CALLS--> C++ pipeline（仅 binding→function→builder 唯一时）
```

新增 `mlir-repomap pipeline-stages <pipeline>`。它输出 Python owner、有序 stage、
证据、C++ pipeline call 与 unresolved-static-name diagnostic。

验证使用 triton-ascend `8ba4ac4ce`：该 checkout 没有 `make_ttgir`，查询返回
not found；实际等价的 Python 入口是 `make_ttir` 与 `ttir_to_linalg`。后者给出 15
个 ordered stage，`triton-to-linalg` 位于第 12 stage（`compiler.py:249`）。这是
源版本事实，未用名称猜测替代。
