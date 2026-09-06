# CompilerDev 使用反馈工件 v1

反馈（feedback）记录消费者**如何使用知识系统**：某个检索是否足够、是否仍需手工搜索、
可能缺了哪类查询。它不是 finding：finding 是关于 compiler 设计风险的文档层工件，带有
生命周期、证据和推理；feedback 不对 compiler 正确性作主张，也绝不进入 graph 或改变
finding 状态。

工件采用 JSON（一个文件一个对象），由
`mlir_repomap.feedback.validate_feedback` 作 stdlib-only 校验。只允许记录非敏感的、
短小的使用观察；不得写入 prompt、会话转录、密钥、个人信息或未脱敏源码内容。

```json
{
  "feedback": {
    "schema_version": 1,
    "created_at": "2026-09-06",
    "task": {
      "kind": "compiler-review",
      "target": "pass:hfusion-merge-vf"
    },
    "query": {
      "command": "review",
      "args": {"name": "MergeVecScope"}
    },
    "observation": "review 返回了 pass memory 与 guard，但仍需搜索 verifier 的具体位置。",
    "manual_source_search": {
      "performed": true,
      "reason": "需要确认 verifier 中的控制流锚点。"
    },
    "possible_gap": {
      "category": "evidence-location",
      "statement": "可能缺少以 pass 为入口直接列出 verifier 位置的确定性查询。"
    },
    "evidence": [
      {"file": "lib/Conversion/HFusion/MergeVecScope.cpp", "lines": "1422"}
    ],
    "sensitivity": {"contains_sensitive_content": false}
  }
}
```

必填字段为 `schema_version`、`created_at`、`task`、`query`、`observation`、
`manual_source_search` 与 `sensitivity`。`query.command` 只能是本 adapter 消费的四个命令：
`review`、`finding-impact`、`pipeline-stages`、`evidence`。`possible_gap` 可以是 `null`；
若存在，需有 category（`query-coverage`、`evidence-location`、`workflow`、
`documentation`、`other`）和简短 statement。`evidence` 是可选的 `file`/`lines` 列表。

反馈可由外部 Harness 保存到其自身、受访问控制的会话工件目录；本仓库不读取、不索引、
不提交这些运行时反馈。
