# CompilerDev 工作流契约

消费方选择与任务匹配的最小只读序列，而不是让 Agent 从源码开始搜索。

| 任务 | 预设序列 | 允许的后续动作 |
|---|---|---|
| Pass review / bug investigation | `status`（fresh）→ `review <pass>` → 对关键 node/edge 执行 `evidence` → 对返回的 finding 执行 `finding-impact` | 打开结果指向的少量文件核验；结论必须区分查询事实和人工/Agent 推理。 |
| Python pipeline audit | `status`（fresh）→ `pipeline-stages <pipeline>` → 对关键 stage 执行 `evidence` → 如存在相关 finding，执行 `finding-impact` | 只审计 AST-confirmed 顺序；运行时控制流必须另行标为未知。 |
| 历史 finding 复核 | `status`（fresh）→ `finding-impact <id>` → `evidence <entity-or-edge>` → 按需 `review <pass>` | 由人或上层 workflow 更新 finding；本 adapter 不更新状态。 |

每个会话应输出三类内容：使用过的命令与 JSON、证据定位、明确的未知项。不得将
`review` 的 retrieval 结果说成新生成的设计判断，也不得因 impact suggestion 自动关闭或
升级 finding。

每个任务先做一个明确、可审核的 route decision：`knowledge_expected=false` 时可以正确 skip；
仅当 `knowledge_expected=true` 且 `compiler_knowledge_calls=0` 时，v2 feedback 才可记录
`adoption-missed`。这是候选使用观察，不能由 validator 或 runtime 推导 compiler 结论。

如果消费者为找到 verifier 或其他关键位置而在 query 已返回的范围外重新搜索源码，应在独立
feedback 中记录它。这是对知识系统覆盖的观察，不是 compiler finding，也不会进入 graph。生产
闭环为：CompilerDev runtime observation → candidate feedback → 人工审核 → curated feedback →
architecture evolution evidence；其中没有自动晋级或自动架构变更。
