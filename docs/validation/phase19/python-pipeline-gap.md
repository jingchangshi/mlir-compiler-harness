# Python Pipeline Gap 与真实验证

## 原有限制

Phase 18 的 `pipeline-composition triton-to-linalg` 只能返回：

```text
Python function ttir_to_linalg
→ binding add_triton_to_linalg
→ C++ factory createTritonToLinalgPass
→ pass triton-to-linalg
```

它不能回答该 pass 在 Python 编排中的第几步，也不能以 `pipeline` 查询 Python
stage 顺序。图中 Python 仅是 `function`，因此 pipeline audit 必须手工阅读源码。

## Phase 19 模型与查询

AST 识别三种静态事实：`pm.add_pass(...)`、`add_*(pm, ...)` 和名为
`pipeline`/`stages` 的有序 list；`make_*` binding 调用仅在确认的
binding→C++ function→builder 链唯一时关联 C++ pipeline。无法解析的名字保留 marker
并成为 diagnostic，而不是猜测 pass。

真实命令：

```text
pipeline-stages make_ttir
pipeline-stages ttir_to_linalg
pipeline-stages make_ttgir
```

结果如下。

| 问题 | 证据化结果 |
|---|---|
| Python 入口在哪里？ | `make_ttir` 在 `third_party/ascend/backend/compiler.py:163`；`ttir_to_linalg` 在 `:194` |
| Pass 顺序是什么？ | `ttir_to_linalg` 共有 15 stage，`:239` control-flow-opt → `:242` annotation → `:249` triton-to-linalg → `:269` dynamic-cv → `:272` debug locations |
| 对应 C++ builder 是什么？ | 当前 `ttir_to_linalg` 的直接事实是逐个 binding→pass，`cxx_pipeline_calls=[]`；没有可证实的一等 C++ builder association |
| make_ttgir 是否存在？ | `pipeline-stages make_ttgir` 返回 not found；当前 checkout 的公开源码没有该函数 |

`make_ttir` 的 10 个 stage 中 9 个是未收录的 upstream/common binding marker，只有
`graph-optimize` 被解析为 pass；这正是 query diagnostic 的用途。`ttir_to_linalg`
只剩一个 distributed binding marker 未解析，其余 14 个 stage 都解析为确定性 pass。

## 回归与边界

AscendNPU-IR 重新索引后为 0 diagnostics、`stale=false`；原 C++
`buildHFusionRegBasePipeline` 仍有 7 stage，`pipeline-stages` 对它明确返回
`not a Python composition pipeline`。因此 C++ pipeline contract 没有被 Python 模型
混淆。

测试覆盖 AST direct add、list order、binding→C++ association、ambiguous name 与
missing evidence；完整测试为 49 passed。仍不支持 runtime conditional execution、
任意 list/dataflow、动态 import 或跨仓 semantic validation。
