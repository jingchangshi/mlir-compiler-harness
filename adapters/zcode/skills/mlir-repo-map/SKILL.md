---
name: mlir-repo-map
description: "Map or refresh the architecture of an MLIR/LLVM compiler repository using the RepoMap engine. Use when the user asks to understand, map, or document a compiler repo's overall architecture: modules, dialects, pipelines, pass catalog, or when docs/compiler-architecture/ is missing or stale. Not for analyzing a single pass (mlir-pass-analysis) or auditing one pipeline (mlir-pipeline-audit)."
---

# mlir-repo-map (thin adapter)

Run the agent-independent `repo-map` workflow. This skill contains no methodology — the
workflow file is the source of truth.

## Entry

1. Locate the harness checkout: `$MLIR_COMPILER_HARNESS`, else
   `<target-repo>/../mlir-compiler-harness`. Abort with a clear message if absent — never
   improvise methodology.
2. Read `$MLIR_COMPILER_HARNESS/docs/workflows/repo-map.md` and execute it exactly.

## Query strategy (fixed)

`mlir-repomap --repo <target-repo>` with: `status` (index first if stale) → `modules
--depth 3` → `dialects` → `pipelines` → `passes` → evidence spot-checks named by the
workflow. No repository-wide grep/find at any point.

## Output convention

`<target-repo>/docs/compiler-architecture/{README,repository-map,dialect-map,pipeline-map,pass-catalog}.md`
with provenance blocks, exactly as the workflow specifies. Preserve existing
`<!-- human-note -->` markers.

## Finish condition

Workflow's verification checklist passes; report queries issued, files opened, and any
missing/insufficient query (that is harness feedback, not user-facing detail).
