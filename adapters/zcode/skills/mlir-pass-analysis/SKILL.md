---
name: mlir-pass-analysis
description: "Deep-analyze one MLIR pass using the RepoMap engine: pipeline position, invariants, algorithm, supported/unsupported cases, test coverage, and evidence-backed defect findings. Use when the user names a specific pass (or asks to analyze/review a pass by name). Not for whole-repo architecture mapping (mlir-repo-map) or single-pipeline audits (mlir-pipeline-audit)."
---

# mlir-pass-analysis (thin adapter)

Run the agent-independent `pass-analysis` workflow for ONE pass. No methodology lives here.

## Entry

1. Locate the harness checkout: `$MLIR_COMPILER_HARNESS`, else
   `<target-repo>/../mlir-compiler-harness`. Abort if absent.
2. Read `$MLIR_COMPILER_HARNESS/docs/workflows/pass-analysis.md` and execute its 13-step
   spine in order for the requested pass.

## Query strategy (fixed)

`mlir-repomap --repo <target-repo>` with: `status` → `pass <name>` (accepts pass arg, td
class, factory, or cpp class name; if ambiguous ask) → `pipeline <name>` / `tests <name>`
for the dossier's neighborhoods. Then read ONLY the evidence-pointed files (≤5 expected).
Repository-wide grep/find is prohibited; a blocked step is reported, not brute-forced.

## Output convention

`<target-repo>/docs/compiler-architecture/passes/<pass-arg>.md` with the workflow's exact
section list and a provenance header (HEAD, indexer version, date, primary files); register
in `pass-catalog.md`. Every load-bearing claim carries `file:line`. Defects use the
Confirmed / Highly Likely / Potential ladder — complexity is not a bug.

## Finish condition

All 13 steps addressed (explicitly mark any step with "nothing found" and why); run report
lists queries issued, files opened, and any missing/insufficient query.
