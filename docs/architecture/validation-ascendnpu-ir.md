# Validation Report — AscendNPU-IR (Phase 2)

Date: 2026-09-05 · Index: 2951 files scanned, 2504 re-extracted, 15.1 s full build, 4.1 MB SQLite index, 0 diagnostics.

## Corpus scope

`.mlir-repomap.toml`: include `bishengir/`, exclude `third-party/`, `build/`, `bishengir/triton/`
(ADR-005). `build/compile_commands.json` exists and is available for a future clangd backend.

## Extracted graph (headline numbers)

| kind | count | | kind | count |
|---|---|---|---|---|
| dialect | 13 | | pattern | 756 |
| pass | 364 | | test | 953 |
| factory | 285 | | pipeline | 62 |
| op | 111 | | interface | 23 |

All 13 in-repo dialects found (HIVM, HFusion, HACC, HIVMAVE, Scope, Symbol, Annotation,
MemRefExt, MathExt, AscendDPX, HIVMRegbaseIntrins, TritonExt, Test). 576 pipeline→pass
membership edges, all pointing at pass entities (no unresolved factory refs).

## What worked (spot-verified against source)

- **hivm-flatten-ops** (`HIVMFlattenOps`, Passes.td:825): summary, `let constructor`
  → `createFlattenOpsPass`, membership in `hivmPostBufferizationOptimizationPipeline`
  (orders 16, 17, scope `func::FuncOp`), pred/succ = hivm-set-buffer-size /
  hivm-aggregated-decompose-op, test `test/Dialect/HIVM/hivm-flatten-ops.mlir`.
- **hfusion-merge-vf** (`MergeVecScope`): memberships in `bufferizationPipeline` under two
  different guards (`hivmPipelineOptions.enableVfMergeLevel == 1` / `== 2`) — the ADR-002
  condition model works on real config-driven pipelines.
- **hfusion-auto-vectorize-v2**: membership in `hfusionAutoVectorizePipeline` with guard
  `hfusionOptions.enableAutoVectorizeV2`, 39 covering tests.
- **buildHFusionRegBasePipeline**: 7 stages with `options.enableFlatten` guards and
  flatten→fold-tensor-empty→canonicalize ordering; caller
  `buildDelayedHFusionRegBaseVectorizePipeline` found.
- **buildBiShengHIRPipeline**: 14 stages incl. macro-level guards
  (`config.getEnableSimdSimtMixCompile()`, `!config.getCompileHost()`).
- Dialect ownership: ops/types/attrs attached to dialects via both `Op<Dialect,...>` and
  multiclass aliases (`HIVM_Op<"...">`).
- Query cost: `pass` dossier ≈1.1 k tokens; `pipeline` ≈1.0 k; `status` ≈0.2 k — a pass
  analysis now needs ~5 targeted queries instead of repo-wide grep.

## What failed / false negatives

1. **Pattern→pass links mostly missing** (756 pattern classes extracted; few PASS_USES_PATTERN
   edges): patterns are registered in free functions (`populateXxxPatterns(RewritePatternSet&)`)
   called from pass bodies, which text extraction does not chase. Biggest single gap.
2. **`runRegBaseCompile` not detected** as pipeline: entry functions with signatures outside
   the `void/LogicalResult/bool` pattern (or dispatch-only bodies) are missed.
3. **Op undercount**: 111 ops vs likely several hundred; ops declared through further
   multiclass indirection or `let opDoc`-style boilerplate are skipped.
4. **Factory name collision**: `createFlattenOpsPass` exists in both `mlir::hfusion::` and
   `mlir::hivm::`. Unqualified call sites are textually ambiguous; resolved by a
   same-dialect locality heuristic and flagged `disambiguation: "same-dialect-heuristic"`
   (confidence reduced). Confirmed edges remain only where the namespace is explicit.

## False positives

- `TEST_COVERS_PASS` links are heuristic by design; some RUN flags map to tool options, not
  passes (filtered against known pass ids, but semantic coverage is not implied).
- A few `pipeline:applyOpFlattenPass`-style nodes are wrapper functions that merely forward
  one pass; acceptable but noisy in the pipeline list.

## Schema / query contract issues found and fixed during validation

- `class_to_pass` mapping originally resolved to file nodes → pipeline edges were rewritten
  onto file entities (caught by FlattenOps validation, fixed).
- Incremental re-index did not invalidate the parse cache when extractor logic changed →
  added `indexer_version` to metadata and invalidation on mismatch (ADR-008).
- td pass summaries polluted by the ctor op-type string → now read `let summary` from the
  def region only.

## Architecture implications (feeds ADR-006/007/008)

- The authoritative pass↔factory link is `let constructor`, not name matching (ADR-006).
- Factory ambiguity needs explicit handling; a `SemanticBackend` would resolve namespaces
  exactly and is the main candidate for the next capability investment (ADR-007).
- `populate*` pattern population needs either call-graph chasing (clangd) or an explicit
  "pattern populate function" extractor — deferred to next phase.
