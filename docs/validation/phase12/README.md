# Phase 12 Validation — Compiler Intent and Optimization Reasoning Graph

(goal text numbers this Phase 11; directory follows the harness's own sequence —
phase11/ is the cross-repo handoff validation.)

Date: 2026-09-05 · AscendNPU-IR HEAD `5671889a3` · triton-ascend HEAD `8ba4ac4ce` ·
indexer v43 · harness tests 12/12.

Question of the phase: **can we reason about compiler design decisions — without
faking certainty?**

## Implemented (ADR-018)

1. **Constraint extraction (deterministic, graph facts)**: `constraint:<file>:<line>`
   entities + `HAS_CONSTRAINT` pass edges for four deterministic kinds inside pass
   classes and their out-of-line method bodies: legality-guards (`return failure()`
   with captured condition), match-failures (with literal reason), terminal
   pass-failures (signalPassFailure with context), TODO/FIXME notes. AscendNPU-IR:
   177 constraints (113 early-return / 50 legality-guard / pass-failure & todo); 171
   resolved to pass level.
2. **Intent model (layered)**: `pass-intent <pass>` returns ONLY graph facts — stated
   intent from TableGen (summary + description now extracted), a deterministic label
   (lowering-boundary [inferred] / rewrite-optimization [inferred] / optimization
   [name/summary heuristic] / structural [heuristic]), boundary evidence, composition
   chains, constraint counts. Agent interpretation is explicitly kept OUT of the graph
   and lives in dossier sections labeled as such.
3. **Optimization opportunities**: deliberately agent-layer records in dossiers
   (Current / Evidence / Impact / Direction) — no engine query, per the
   no-consumer-no-query rule. `pass-constraints` is the deterministic substrate.

## Validation

| pass | intent label | deterministic constraints |
|---|---|---|
| hfusion-merge-vf | optimization (heuristic) | 2 legality-guards (dependency-pair skip, VF-num limit) |
| hfusion-auto-vectorize-v2 | optimization (heuristic) | 1 legality-guard (verifier acceptance) |
| vf-fusion | rewrite/optimization (inferred) | 4 legality-guards (generalization exclusions) |
| triton-to-linalg | rewrite/optimization (inferred) | 0 in coverage (guards live in unspanned helpers — known limit) |
| triton-to-annotation | lowering/conversion boundary (inferred) | 1 legality-guard (partial conversion) |

Dossiers updated with "Phase 12: Intent & Constraints" sections; each separates graph
facts from agent interpretation and records opportunities (e.g. merge-vec-scope: the
*missing* single-use guard is visible only by absence — a reasoning result, correctly
not a graph fact).

## Engine fixes during validation

- RE_FAIL widened (bare `signalPassFailure()`, `failure(args)`); constraint scan
  rewritten as a self-contained pass with out-of-line method spans (class bodies alone
  missed the guards — AutoVectorizeV2 case).
- intent label layering: graph-derived labels first, name/summary keywords as clearly
  marked heuristic fallback (AutoVectorizeV2 was misleadingly "structural" before).

## Honest limitations

- Multi-line guard conditions truncated to the first line.
- Guards inside helpers outside method-span coverage are missed (triton-to-linalg).
- Constraints are per-occurrence facts, not semantic equivalence classes; grouping is
  agent work.
