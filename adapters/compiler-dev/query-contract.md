# CompilerDev 查询契约 v1

本契约只依赖稳定 CLI JSON 输出中的 `command`、`index` 和 `result` 字段。调用方必须将
`index.stale=true` 视为“当前工作树未被该索引覆盖”，先运行：

```bash
mlir-repomap index --full
```

随后使用下面四个命令。命令只读取 graph 与文档层工件；它们不会生成 reasoning、修改
finding 状态或写入 graph。

| 任务问题 | 命令 | 可消费结果 | 必须保留的不确定性 |
|---|---|---|---|
| 这个 pass 已有哪些 review memory、守护条件和关联 finding？ | `mlir-repomap review <pass> [--dir D] [--docs-dir D] [--git-repo R] [--since REF]` | pass identity、逐字 review record、约束、关联 finding 和 impact signal | 空 memory 是显式 note；文档布局或跨仓引用不能解析时是 diagnostic，不能补猜。 |
| 某 finding 受哪些结构变化影响，建议审查哪里？ | `mlir-repomap finding-impact <id> [--dir D] [--git-repo R] [--since REF]` | entity refs、文件 drift、constraint diff、tests 与 review-scope suggestion | suggestion 不是正确性 verdict；没有信号是有效负结果；不解析的 ref/baseline 必须报告。 |
| Python 编排的静态 stage 顺序是什么？ | `mlir-repomap pipeline-stages <pipeline>` | AST-confirmed owner、有序 stage、`file:line` 证据、确认的 C++ pipeline call | 只代表静态 AST；dynamic import、分支执行、任意数据流和未解析 binding 名称不能推断。C++ pipeline 会明确说明不是 Python composition。 |
| 一项事实的可追溯证据与相关 finding 是什么？ | `mlir-repomap evidence <node-or-edge-id>` | entity、`file:line`/snippet 证据、结构匹配的 finding、主文件近期 git history | 匹配只按 ref/file/entity equality；不是 embedding 或语义相似度，可能有 file-level over-match。 |

CLI 的完整全局选项和 JSON envelope 仍以
[Query API](../../docs/architecture/query-api.md) 为准。调用方应将每个命令的原始 JSON
与仅含必要 `file:line` 的工作记录一同保留；不要把模型摘要反写为查询事实。
