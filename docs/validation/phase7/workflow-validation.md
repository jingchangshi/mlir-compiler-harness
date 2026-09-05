# Phase 7 Validation — Provenance-aware Workflow Intelligence

Date: 2026-09-05 · AscendNPU-IR HEAD `5671889a3` · indexer v19 · harness tests 12/12.

## Question of the phase

Phase 6 proved "can we know the fact"; Phase 7 asks "does the agent **consistently use**
the fact". Method: the three workflows were upgraded first (query strategy now mandates
`pattern-owner`, `attribute`, `pipeline-builder`), then re-executed on AscendNPU-IR.

## Workflow changes (source of truth, docs/workflows/)

- `pass-analysis.md`: new step **7b Pattern provenance** (ownership path, per-hop
  evidence/confidence, "graph-confirmed zero patterns" phrasing), new step **5b Attribute
  contract** (producer/consumer/attachment via `repo attribute`), step 3 extended with
  `pipeline-builder` (insertion-site justification), budget updated.
- `pipeline-audit.md`: mandatory pipeline provenance chain (builder → nested → insertion
  sites), ordering lens now requires the **swap experiment** outcome, lens 2 upgraded to
  attribute contracts via `repo attribute`, output spec gains builder provenance.
- `repo-map.md`: new step 6b — generate `pattern-map.md` + `attribute-map.md`.

## Validation results

### Pass analyses ×6 (dossiers updated with "Workflow Validation (Phase 7)" sections)

| pass | pattern-owner used | attribute used | pipeline-builder used | new facts |
|---|---|---|---|---|
| MergeVecScope | n/a (zero patterns, graph-confirmed) | yes: reduction-selection attrs | yes (bufferizationPipeline) | "no attribute contract for this pass" now explicit |
| HFusionFlattenOps | yes: full chain w/ call-site evidence (FlattenOps.cpp:114) | graph-confirmed none | yes ×2 (582, 402) | ownership hop evidence now includes call site |
| MarkStrideAlign | zero patterns confirmed | yes: StrideAlignDimsAttr chain incl. HIVMToStandard.cpp:2083 | yes (alignStorage regbase @480) | "why two mark passes" answered from builder body |
| EnableStrideAlign | 2 direct confirmed pattern uses | yes | yes | module-scope-after-fold justification |
| AutoVectorizeV2 | zero patterns confirmed | yes: kRegisterTreeReductionSelectedAttr creators | yes (402) | attribute channel now a query, not a code comment |
| VFFusion | confirmed chain (populateEmptifyReduceInitPatterns) | yes: 3 reduction-tree attrs | yes (402) | separation from PreVectorizationFusion visible |

### RegBase pipeline audit re-run

`pipelines/regbase-hivm-post-bufferization.md` gained a Phase 7 provenance section:
4 builder chains (all confirmed, file:line), 4 ordering justifications with swap outcomes,
3 attribute contracts inventoried. The dual `alignStoragePipeline` is handled as two
explicit file-qualified pipelines — the Phase 5 artifact cannot recur by construction.

### New architecture docs (repo-map workflow step 6b)

- `docs/compiler-architecture/pattern-map.md`: 142 passes with ownership chains,
  190 graph-confirmed zero-pattern passes.
- `docs/compiler-architecture/attribute-map.md`: 86 attribute entities, 43 with confirmed
  creator pass classes (top: VectorFunctionAttr, TFuncCoreTypeAttr,
  HIVMTightlyCoupledBufferAttr).

## Query usage (workflow-driven)

Automatically consumed by workflows now: `pass`, `pipeline`, `pipeline-builder`,
`pattern-owner`, `attribute`, `tests` (with features), `status`/`index`, `changed`.
Still unused by workflows: `modules --depth` (repo-map only), `symbol`/`references`
(occasional), `evidence` (drill-down only). No new query was needed in this phase —
the Phase 6 surface proved sufficient (see remaining-gaps.md for the two small gaps found).

## Engine fixes during validation (small, generic)

1. `pattern-owner` now walks the FUNCTION_CALLS chain upward, so the pass appears even
   when the pattern is defined in a nested helper (registerOne case).
2. `attribute` entities now also capture the `kXxxAttr` constant idiom — this is what made
   the VFFusion↔AutoVectorizeV2 channel queryable.
3. `CREATES_ATTRIBUTE` evidence downgraded to `inferred` (a class-body mention is not
   proof of creation); docs updated to match.
4. `pipeline <qualified-id>` no longer crashes on fall-through (None-guard).

## Remaining gaps (remaining-gaps.md)

- `PIPELINE_BUILT_BY` evidence snippet is a bare `{` (cosmetic; the builder node carries
  the right line).
- Attribute creator side remains `inferred` — distinguishing creation from consumption
  textually needs op-level (createAlignMarkOp-style) tracing, deferred.
- Workflow budget: analyses now issue ~6-10 queries per pass (up from ~4) — acceptable,
  still far below grep cost.
