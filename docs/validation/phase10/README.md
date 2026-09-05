# Phase 10 Validation — Compiler Semantic Boundary Graph

Date: 2026-09-05 · AscendNPU-IR HEAD `5671889a3` · triton-ascend HEAD `8ba4ac4ce` ·
indexer v35 · harness tests 12/12.

Question of the phase: **can we understand compiler semantic boundaries?**

## Implemented (ADR-016, generic)

1. **Dialect transition graph** (Phase 8 EG-2 closed): `DIALECT_TRANSITIONS_TO` edges,
   two evidence paths —
   (a) confirmed: `ConversionTarget` idiom (`addLegalDialect`/`addIllegalDialect`,
   namespace-qualified names supported; attributed to the enclosing pass class);
   (b) inferred: derived from pattern op ownership (PATTERN_MATCHES_OP → input dialect,
   PATTERN_CREATES_OP → output dialect) through the populator chains.
   Role property (`input`/`output`); dialect→dialect pairs derived at query time.
2. **Attribute semantic contract**: lightweight `role` on attribute entities from a
   keyword table (memory alignment / core-type assignment / annotation carrier /
   layout / tiling / sync / vector-function / storage-alignment markers), confidence
   `heuristic`; query `semantic-contract <attr>` returns role + producers + consumers.
   No attribute-value evaluation.
3. **IR boundary contract**: query `boundary <pass>` = input dialects + output dialects +
   transition pairs + created ops + downstream assumptions (successor passes).
4. **Workflow integration**: pass-analysis step 7a (semantic boundary analysis with the
   "lowering boundary because…" statement format); pipeline-audit lens 1a (dialect
   evolution + hardware boundary); queries documented in query-api.md.

## Validation

| target | result |
|---|---|
| triton-to-annotation | input `TritonAscend` (inferred) → output `Annotation` (**confirmed**, TritonToAnnotation.cpp:64); transition pair derived; boundary names the attribute-payload contract |
| triton-to-linalg | input `Triton` (inferred via matched ops); output side = external-dialect handoff (honest: Linalg td lives outside the corpus) — dossier states the boundary explicitly |
| AscendNPU-IR StrideAlignDimsAttr | role "memory alignment contract" (heuristic), 3 producers / 9 consumers |
| AscendNPU-IR TFuncCoreTypeAttr | role "core-type assignment" (heuristic), 6 producers / 20 consumers |
| AutoVectorizeV2 (RegisterTreeReductionSelectedAttr) | no keyword role — dossier documents the strategy-marker role by agent reasoning (intended division of labor) |
| AscendNPU-IR regression | index 57 s; RegBase builders intact; 12/12 tests |

## Honest limitations

- Output-dialect derivation depends on created-op ownership; ops from dialects whose td
  lives outside the corpus yield no output dialect (cross-repo boundary case, QG-7).
- Role table is a keyword heuristic — a strategy/plan attribute like
  RegisterTreeReductionSelectedAttr gets no automatic role; agent reasoning fills it.
- `convert-to-hivm-op` (a thin pipeline wrapper) reports input `Annotation` (its patterns
  genuinely see marks) and no output — wrapper passes don't own ConversionTargets; the
  transition belongs to the inner converter passes.
