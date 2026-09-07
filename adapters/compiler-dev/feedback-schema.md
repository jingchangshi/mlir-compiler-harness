# CompilerDev 使用反馈工件 v1 / v2

反馈（feedback）记录消费者**如何使用知识系统**，不是 compiler finding。它不会进入 graph、创建 node、修改 finding 或成为 compiler correctness evidence；本仓也不会把它写入 SQLite index。反馈只服务于知识查询与工作流的覆盖度评审。

工件采用 JSON（一个文件一个对象），由 `mlir_repomap.feedback.validate_feedback` 作 stdlib-only 校验。外部 consumer 在自己的、受访问控制的会话工件目录保存运行时记录；本仓只维护协议和验证器。

## v1：保持兼容

`schema_version: 1` 的既有协议不变：`query` 必填，原有已提交 feedback artifacts 都可继续通过。它适合表达一次已执行查询是否足够，却不能表达“本应查询但完全没有调用”的情况。

```json
{
  "feedback": {
    "schema_version": 1,
    "created_at": "2026-09-06",
    "task": {"kind": "compiler-review", "target": "pass:hfusion-merge-vf"},
    "query": {"command": "review", "args": {"name": "MergeVecScope"}},
    "observation": "review 返回了 pass memory 与 guard，但仍需搜索 verifier 的具体位置。",
    "manual_source_search": {"performed": true, "reason": "需要确认 verifier 中的控制流锚点。"},
    "possible_gap": {"category": "evidence-location", "statement": "可能缺少 verifier 位置查询。"},
    "evidence": [{"file": "lib/Conversion/HFusion/MergeVecScope.cpp", "lines": "1422"}],
    "sensitivity": {"contains_sensitive_content": false}
  }
}
```

## v2：可路由的最小使用观察

`schema_version: 2` 增加 `observation_kind`、`route`、`usage`、`operational` 与 `origin`。v2 顶层及其结构化子对象采取 strict allowed-fields 校验，因而诸如 `prompt`、`transcript`、`source_text`、`messages` 的字段不能写入工件。

```json
{
  "feedback": {
    "schema_version": 2,
    "created_at": "2026-09-07",
    "origin": "automatic",
    "observation_kind": "query-operational",
    "task": {
      "kind": "compiler-review",
      "target": "pass:hfusion-merge-vf",
      "classification": {"confidence": "high", "source": "heuristic"}
    },
    "query": {"command": "review", "args": {"name": "MergeVecScope"}},
    "route": {"knowledge_expected": true, "kind": "pass-review", "confidence": "high"},
    "usage": {
      "compiler_knowledge_calls": 1,
      "knowledge_commands": {"review": 1},
      "first_knowledge_step": 3,
      "discovery_search_calls": 0
    },
    "operational": {
      "stale_index": true,
      "refresh_performed": true,
      "refresh_duration_ms": 97000,
      "duration_ms": 100400
    },
    "observation": "索引刷新后查询成功，记录运行成本，不作架构结论。",
    "manual_source_search": {"performed": false},
    "possible_gap": null,
    "evidence": [],
    "sensitivity": {"contains_sensitive_content": false}
  }
}
```

### observation_kind 与 query

| `observation_kind` | 语义 | `query` |
|---|---|---|
| `query-sufficient` | 已执行查询足以支持该任务的知识获取。 | 必填对象。 |
| `query-insufficient` | 已执行查询，但仍暴露覆盖或定位缺口。 | 必填对象。 |
| `query-operational` | 已执行查询，记录 stale、刷新、截断、错误等运行信号。 | 必填对象。 |
| `adoption-missed` | 路由判断应使用知识系统，但会话未调用它。 | 必须为 `null`。 |

`adoption-missed` 还必须同时满足 `route.knowledge_expected=true` 和 `usage.compiler_knowledge_calls=0`。反过来，`knowledge_expected=false` 且零调用是正确 skip，绝不是 failure。验证器只检查字段一致，**不**从会话内容推断 Agent 是否真的应当调用。

`task.kind` 与 `task.target` 继续必填。可选的 `task.classification` 使用 `confidence`（`low`、`medium`、`high`）和 `source`（`heuristic`、`human`、`policy`）。机器分类必须使用显式的 `source: "heuristic"`，不能伪装成 compiler fact。

### route、usage 与 operational

`route` 在 v2 必填：`knowledge_expected` 是布尔值，`kind` 为稳定、非敏感的路由类别，`confidence` 为 `low`、`medium` 或 `high`。它记录“该任务是否预期使用知识”，而非任务结论。

`usage` 在 v2 必填，但其中的统计字段均为可选；允许的最小字段为：`compiler_knowledge_calls`、`knowledge_commands`（四个 adapter command 的计数）、`discovery_search_calls`、`search_after_query_calls`、`first_knowledge_step`、`first_discovery_step`、`first_edit_step`。计数必须是非负整数，step 必须是正整数。`adoption-missed` 例外地要求显式给出零次 `compiler_knowledge_calls`。

可选 `operational` 只记录紧凑信号：布尔值 `stale_index`、`refresh_performed`、`not_found`、`truncated`、`error`，以及非负整数 `refresh_duration_ms`、`diagnostic_count`、`duration_ms`。不保存错误正文、命令文本或查询结果内容。

### candidate 与 curated

`origin` 必填，取值为 `automatic`、`agent`、`curated`。前两者是待审核 candidate；只有维护者审核、去敏并明确标记为 `curated` 后才可作为 architecture evolution 的人工证据。协议没有 `candidate → curated` 的自动转换，也不允许任何 feedback 自动改变 graph 或 finding。

### 隐私边界

`sensitivity.contains_sensitive_content` 必须严格为 `false`。只可保存任务稳定标识、计数、步骤编号、有限的运行布尔/时长与 `file:line` 指针；不得保存 prompt、完整 transcript、源码/source text、shell command text、API key、secret 或个人信息。`observation` 与 `possible_gap.statement` 也只能是简短、去敏后的结论性描述。
