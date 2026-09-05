# Phase 5 Workflow Gaps

Gaps found in `docs/workflows/{pass-analysis,pipeline-audit}.md` while executing them.
None blocked completion; all are methodology refinements.

## WG-1 — Analysis-dependency reasoning is underspecified

- Missing step: how to analyze an MLIR *analysis* dependency (getAnalysis<>) and its
  invalidation boundary across a pipeline (goal §10's example). We handled it by reading
  the pass body, but the workflow's step 5 ("Analysis dependencies") gives no method for
  the invalidation question.
- Impact: pass contracts risk missing "analysis X computed before pass Y is stale after Z".
- Fix: extend step 5 with a recipe: find `getAnalysis<>` uses → locate the pipeline
  position of the analysis-preserving invalidation → name the pass that would invalidate.

## WG-2 — IR examples lack a deterministic source convention

- Missing step: the "IR Examples" section does not say where before/after IR should come
  from. We used lit CHECK lines (deterministic, already linked by RepoMap) — that worked
  well and should be the convention; inventing IR by hand is the failure mode to avoid.
- Fix: add to the output spec: "prefer before/after pairs taken from linked lit tests'
  CHECK comments; hand-written IR only for counterexamples, marked as such."

## WG-3 — Ordering-swap thought experiment not codified

- Missing step: pipeline-audit's ordering lens asks *why* A precedes B but does not require
  the swap experiment ("what happens if exchanged?"), which proved to be the sharpest tool
  in this phase's audit (5 concrete swap outcomes).
- Fix: add to lens 1: "for each load-bearing pair, state the concrete failure (silent /
  compile error / no-op) if the order is swapped."

## WG-4 — Coverage checklists are per-pass-family ad hoc

- Missing step: goal §5.1-style coverage dimensions (multi-user, reduction, dynamic shape,
  nested regions, scope interaction) recur across merge/vectorize/align pass families, but
  each dossier had to invent its own checklist. A small standard checklist per family
  (referenced from pass-analysis.md) would make coverage sections comparable.
- Fix: add an appendix table "family → standard coverage dimensions".

## WG-5 — Evidence budget for large passes

- Observation: 800–1600-line pass files were read almost fully (mark-stride-align 1119
  lines, merge-vec-scope 1634). The "≤5 files" budget holds, but nothing bounds bytes.
  For capability-limited models a per-section read order (runOnOperation first, options
  second, helpers last) would help.
- Fix: add a reading order convention to pass-analysis.md step 6.
