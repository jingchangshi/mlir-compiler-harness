# Phase 6 Validation — Provenance-aware Compiler Knowledge Graph

Date: 2026-09-05 · AscendNPU-IR HEAD `5671889a3` · indexer v18 · harness tests 12/12.

## Goal: from Entity Graph to Entity + Provenance Graph

P0 implemented and validated (engine changes per ADR-012); Phase 5's six pass analyses
re-executed through the same skill conventions; dossiers updated with a
"Provenance Update (Phase 6)" section each.

## QG-by-QG results

| gap | fix | validation on AscendNPU-IR |
|---|---|---|
| QG-3 pattern ownership | pattern-set functions identified by `RewritePatternSet&` signature (name-agnostic); FUNCTION_DEFINES_PATTERN + FUNCTION_CALLS + PASS_USES_PATTERN_POPULATOR edges; cross-file populate* call markers resolved at graph level | hfusion-flatten-ops: confirmed chain FlattenOpsPass → `populateFlattenOpsPattern` → (inferred) `registerAll` → `registerOne` → `FlattenElemwiseOpPattern`; vf-fusion: confirmed chain to `populateEmptifyReduceInitPatterns`; enable-stride-align: 2 confirmed direct pattern uses; merge-vf / mark-stride-align / auto-vectorize-v2: graph-confirmed **zero patterns** (previously indistinguishable from an extraction gap) |
| QG-1 pipeline identity | `pipeline:<file>:<name>` identity; bare-name query returns unique match or explicit ambiguity; `pipeline-builder` query | `alignStoragePipeline` now yields two candidates; regbase instance stages seq-ordered AlignAllocSize(1)→PreMark(2)→Mark(3)→FoldAllocReshape(4)→Enable(5) — the Phase-5 false "order 1 and 2" artifact is gone |
| QG-4 attribute provenance | `attribute:<Name>` entities from `<Name>Attr::name` refs + CREATES_ATTRIBUTE from pass bodies | `repo attribute StrideAlignDimsAttr`: 9 referencing files w/ evidence; confirmed creators MarkStrideAlignPass/EnableStrideAlignPass; consumer `ConvertHIVMToStandardPass` (HIVMToStandard.cpp:2083) — the audit's downstream-failure question is now a query |
| QG-5 test features | heuristic feature tags (dynamic-shape/reduction/fusion/vectorization/bufferization/stride-align/nested-region) in test nodes, returned by `tests` | enable-stride-align tests tagged `stride-align,bufferization,dynamic-shape,...` |
| QG-6 cross-scope order | `seq` property: monotonic source order across scopes on PIPELINE_CONTAINS | regbase alignStorage stages expose a single total order |

## Before / After (goal §8 comparison)

- FlattenOps pattern owner: **heuristic/absent → confirmed chain** (file:line at every hop).
- MergeVecScope: **"no patterns" was ambiguous → graph-confirmed zero**.
- Mark/EnableStrideAlign attribute chain: **manual grep → `repo attribute` query**.
- VFFusion: **two same-named "vf fusion" passes conflated → separated** (td classes
  `VFFusion` vs `PreVectorizationFusion` share a factory file family; now distinct nodes).
- alignStoragePipeline: **silent merge → explicit two candidates**.

## Issues found & fixed during validation (engine)

1. Cross-file populator calls needed a name-marker + resolution step (definition and call
   live in different files).
2. Template-forwarding chains (`registerAll<T...> -> registerOne<T>`) required (a) a
   name-agnostic signature-based populator definition and (b) template-arg-tolerant call
   matching.
3. Ambiguous cpp pass class names across dialects (two `FlattenOpsPass`) required the
   same-dialect locality heuristic at *class* level (extension of ADR-007) — flagged
   `disambiguation` on affected edges.
4. `CREATES_ATTRIBUTE` edge kind was initially missing from the schema constants (caught
   by the real-repo rebuild).

## Remaining gaps (honest)

- Populator chain traversal stops at helpers whose signature does not take
  `RewritePatternSet&` (e.g. builders that construct a set internally) — rare.
- Attribute references are name-level (no attribute *value* or per-op attachment points).
- `RENDERED` per-op attribute attachment (Operation HAS_ATTRIBUTE) is not modeled —
  only pass-level creation is.
- Function entities exist only for pattern-set helpers and pipeline builders (not a
  general symbol table) — deliberate scope control.
