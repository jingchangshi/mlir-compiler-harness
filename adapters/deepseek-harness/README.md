# DeepSeek Harness Adapter

Thin adapter that runs the agent-independent workflows (source of truth:
`<harness>/docs/workflows/`) inside a DeepSeek-Harness-style coding agent, regardless of the
underlying model (DeepSeek / GLM / Qwen).

## Layout

```
goal-templates/
├── repo-map-goal.md         # paste as goal: build/refresh repository architecture docs
├── pass-analysis-goal.md    # paste as goal: deep-analyze one pass
└── pipeline-audit-goal.md   # paste as goal: audit one pipeline
conventions.md               # CLI/tool usage rules the goal templates reference
```

## Prerequisites

1. The target MLIR repository has `mlir-repomap` on PATH (see `repomap/` in the harness repo)
   and an index (`.mlir-repomap/`).
2. The harness checkout is reachable. Resolution order (see conventions.md):
   `$MLIR_COMPILER_HARNESS` → `$MLIR_COMPILER_HARNESS/workflows` snapshot → fail with a
   clear message. Goal templates instruct the agent to abort if the workflow files cannot
   be located — **the agent must never improvise methodology from memory**.

## How to use

Paste the goal template that matches the task, filling the bracketed placeholders:

```
分析 FlattenOps Pass，重点说明 pipeline 位置、核心算法、覆盖场景和潜在设计缺陷。
```
→ use `pass-analysis-goal.md` with `PASS_NAME=FlattenOps`.

## Why templates are short

They only start the agent, point it at the workflow, fix the CLI query strategy, the output
location and the verification rules. The methodology lives in `docs/workflows/` and is read
at run time; nothing is duplicated here (thin-adapter rule, harness ADR-010).
