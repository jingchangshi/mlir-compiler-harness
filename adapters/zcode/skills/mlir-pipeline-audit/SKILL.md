---
name: mlir-pipeline-audit
description: "Audit one MLIR compiler pipeline for cross-pass risks using the RepoMap engine: implicit contracts, fragile ordering, guarded duplication, duplicate analyses, premature lowering, missing verification, architecture leakage, coverage gaps. Use when the user asks to audit/review a pipeline (or the pipeline around a pass) rather than analyze one pass deeply. Not for whole-repo mapping (mlir-repo-map) or single-pass dossiers (mlir-pass-analysis)."
---

# mlir-pipeline-audit (thin adapter)

Run the agent-independent `pipeline-audit` workflow. No methodology lives here.

## Entry

1. Locate the harness checkout: `$MLIR_COMPILER_HARNESS`, else
   `<target-repo>/../mlir-compiler-harness`. Abort if absent.
2. Read `$MLIR_COMPILER_HARNESS/docs/workflows/pipeline-audit.md` and execute its 8 audit
   lenses (each ends in a finding or an explicit "checked, OK").

## Query strategy (fixed)

`mlir-repomap --repo <target-repo>` with: `pipeline <name>` → `tests <name>` → `changed
[base]` for recent-risk focus. Read only the pipeline-builder regions the evidence names.
Do not re-summarize each pass (that is mlir-pass-analysis). No repository-wide grep.

## Output convention

`<target-repo>/docs/compiler-architecture/pipelines/<pipeline-name>.md` with sections
`# Pipeline Overview` (stages + verbatim guards) · `# Findings` (numbered: Problem /
Evidence / Trigger / Impact / Confidence / Fix direction) · `# Invariant Map` ·
`# Coverage` · `# Recommendations`; register in `pipeline-map.md`.

## Finish condition

All 8 lenses addressed; stage overview matches query output exactly; run report lists
queries issued, files opened, and any missing/insufficient query.
