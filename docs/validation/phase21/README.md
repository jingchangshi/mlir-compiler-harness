# Phase 21 验证记录：Compiler Knowledge Feedback Protocol v2

日期：2026-09-07。范围仅为 `mlir-compiler-harness` 的 feedback contract、验证器与 adapter
文档；没有修改 `compiler-dev-harness`，没有新增 graph node/edge，也没有改动 SQLite index 或
finding 生命周期。

## 交付物与验证

| 交付物 | 实现证据 | 验证证据 |
|---|---|---|
| v1 兼容 | `validate_feedback` 按 `schema_version` 分派，保留 v1 既有嵌套字段行为。 | 读取 sibling `analysis/feedback/*.json` 的 8 个已提交工件，全部通过。包含 MergeVecScope sufficient、AutoVectorizeV2 sufficient、Triton pipeline-stage coverage gap 与 Phase-20 早期 routing feedback。 |
| 四类 v2 观察 | `query-sufficient`、`query-insufficient`、`adoption-missed`、`query-operational`。 | adapter 单测覆盖四个有效样本。 |
| adoption-missed | 统一 `query: null`；要求 `route.knowledge_expected=true` 与 `usage.compiler_knowledge_calls=0`。 | 单测拒绝 false route、非零调用和实际 query；正确 skip 不会成为 failure。 |
| route 与分类 | route 记录预期与置信度；`task.classification.source` 对机器分类强制 `heuristic`。 | 单测拒绝非法 confidence。 |
| 最小统计与运行信号 | usage 仅接受计数、命令计数与 step；operational 仅接受布尔/时长/诊断计数。 | 单测拒绝布尔伪计数等 malformed usage。 |
| 隐私与严格字段 | v2 的顶层/嵌套 allowed fields，且敏感标记必须为 false。 | 单测拒绝 `prompt`、敏感标记和未知 schema version。 |
| candidate/curated | `origin: automatic|agent|curated`；前两者只为 candidate。 | feedback-schema、workflow-contract、direction 与 ADR-025 均明确无自动晋级/架构 mutation。 |

执行的专项命令：

```bash
PYTHONPATH=repomap/src python3 -m unittest -v repomap.tests.test_compiler_dev_adapter
PYTHONPATH=repomap/src python3 - <<'PY'
import json
from pathlib import Path
from mlir_repomap.feedback import validate_feedback

root = Path('../compiler-dev-harness/analysis/feedback')
for path in sorted(root.glob('*.json')):
    assert not validate_feedback(json.loads(path.read_text(encoding='utf-8')), str(path))
print('v1 corpus passed')
PY
```

结果：adapter 专项 12/12 通过；sibling v1 compatibility corpus 8/8 通过。完整 pytest 在本
phase 最终复核时另行执行。

## 明确保留的限制

- validator 只验证 schema consistency，不能从统计推断真实的 Agent 行为、任务语义或 compiler
  correctness；
- runtime session/raw telemetry 仍由 consumer repo 保存，本仓不读取、不索引也不提交它；
- 只有人工审核并去敏的 `origin: curated` feedback 才可在后续架构评审中使用，automatic/agent
  candidate 永远不直接驱动 graph、finding 或 architecture mutation。
