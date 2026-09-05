# RegBase Pipeline Audit — Phase 5 ZCode-driven validation

> Provenance: `mlir-pipeline-audit` skill → `pipeline-audit` workflow. HEAD `5671889a3` ·
> 2026-09-05. Complements the Phase 3 audit (`architecture docs` of the target repo,
> `pipelines/regbase-hivm-post-bufferization.md`); this audit focuses on pass contracts,
> ordering necessity, and the abstraction boundary. Evidence: dossier set produced in this
> phase (`mark-stride-align`, `enable-stride-align`, `hfusion-flatten-ops`,
> `merge-vec-scope`, `vf-fusion`, `auto-vectorize-v2`) + pipeline graphs
> (`bufferizationPipeline`, `hfusionAutoVectorizePipeline`, `alignStoragePipeline`,
> `buildHFusionRegBasePipeline`, `hivmPostBufferizationOptimizationPipeline`).

# Pipeline Overview (contract-relevant fragment)

```
[vf-fusion] ──> [hfusion-flatten-ops] ──> [hfusion-auto-vectorize-v2]
     (tensor IR, generalization+fusion)   (axis merge)          (transform-dialect vectorize)
[bufferizationPipeline]:
  (L1) merge-vf(==1) -> copy-insertion -> OneShotBufferize(2) -> ... -> OneShotBufferize(4)
       -> merge-vf(==2) -> convert-to-hivm-op ...
[alignStoragePipeline]:
  AlignAllocSize -> (PreMark -> MarkStrideAlign | enableHIVMAutoStorageAlign)
  -> FoldAllocReshape -> EnableStrideAlign
[post-bufferization HIVM]:
  ... set-buffer-size -> hivm-flatten-ops -> aggregated-decompose(AFTER_HIVM_FLATTEN_OPS) ...
```

# Pass Contracts (A creates X → B assumes X)

| # | producer | creates | consumer | assumes | verified? |
|---|---|---|---|---|---|
| C1 | vf-fusion | `linalg.generic` payload + reduction-selection attrs | auto-vectorize-v2 | attrs present; removes them after | by cleanup code (AV2:1402-1410); **stale if AV2 off** |
| C2 | hfusion-flatten-ops | flat iteration spaces (collapse/expand pairs) | auto-vectorize-v2 planner; **hivm-mark-stride-align** (cross-dialect!) | "A5 memrefTypes already flattened" (MarkStrideAlign.cpp:932-935) | **no** — comment-only contract |
| C3 | mark-stride-align | `annotation.mark`(stride_align) | enable-stride-align | marks exist & valid | propagation failure test exists |
| C4 | enable-stride-align | padded alloc + subview + `hivm.storage_aligned` | lowering (`HIVMToStandard` reads StrideAlignDimsAttr) | marks materialized or absent | **no verifier** |
| C5 | merged call graph (merge-vf) | single-call VFs | bufferization | single-use VFs | **unchecked assumption** (MergeVecScope.cpp:619-621) |
| C6 | auto-vectorize-v2 | vector regions | bufferization/decompose | bufferizable vector IR | AV2 verifier at accept time |

# Ordering Dependencies (what breaks if swapped)

- **vf-fusion before flatten**: generalization is rank-aware (`isElementwise`, loop count);
  after flatten all spaces are 1-D and generalization would be a no-op — swap degrades, not
  corrupts. Directionally safe.
- **flatten before auto-vectorize-v2**: AV2 plans per-block tile/fuse on flat spaces;
  swapping would tile 2-D spaces then flatten inside vector regions — the flatten pass has
  no vector-region support → likely pass failure (safe but wasted).
- **mark-stride-align after flatten (cross-dialect)**: swapping violates C2 silently —
  the regbase mark path would compute align dims on 2-D shapes while downstream expects
  flat-axis marks → **wrong axis alignment, silent** (F1 of this audit).
- **PreMark → Mark → FoldAllocReshape → Enable**: FoldAllocReshape between mark and enable
  means marks must survive a reshape fold; propagation handles view rewrites, but the
  ordering is load-bearing for the subview-fix path (mark dossier step 5). Swapping
  FoldAllocReshape before Mark would remove the views the fix pattern matches.
- **merge-vf(level1) before copy-insertion**: merging on tensor IR avoids per-copy alias
  inflation; swapping would make the dependency closure see inserted copies as dependencies
  and merge nothing (capability loss, not corruption).
- **OneShotBufferize ×2 (orders 2 & 4)**: guarded duplication (audit lens 3): the second
  round covers IR produced between the rounds (e.g. merged VFs at order 5 run after round
  2 by design). Guards on merge are mutually exclusive by value; the bufferize rounds
  themselves are unguarded — needs owner confirmation (carried over from Phase 3 audit F2).

# Abstraction Boundary

The high-level→hardware transition is **staged, and partly inverted**:

1. `vf-fusion`: pure tensor-level fusion (highest abstraction).
2. `hfusion-flatten-ops`: **first abstraction drop** — named-op/axis semantics collapse to
   flat spaces; only reassociation pairs remember N/M axes. After this point, per-axis
   (M/N/tile) optimizations must reconstruct axes from collapse chains.
3. `auto-vectorize-v2`: vector-level abstraction created (vector<Nxf32> regions).
4. bufferization + `hivm-flatten-ops` (HIVM): buffer-level, hardware-shaped memory.
5. `mark/enable-stride-align`: **hardware-geometry injection** — 512N+32 vsstb rules,
   Fixpipe N/M tables, UB 32-byte alignment enter as annotations/shapes.
6. `aggregated-decompose` (phased enum): ISA-shape decomposition.

Premature-lowering risk (goal §7): the flatten at step 2 happens **before** vectorization
planning, so any future per-axis vector-cost model must reverse-engineer axes — this is the
main "lost optimization opportunity" boundary. Conversely, stride alignment (step 5) is
correctly late. The A5 flatten-before-storage-align inversion is intentional (flatten makes
the align decision 1-D) but creates the fragile C2 contract.

# Architecture Issues

- **A1 [Architecture | Highly Likely]** C2 is a cross-dialect, comment-only contract with a
  silent wrong-axis failure mode (regbase mark path assumes flatten; `enableFlatten` is
  independently guarded). Highest-leverage fix: assert flatten evidence (e.g. presence of
  collapse_shape or a marker) in mark-stride-align's regbase path.
- **A2 [Architecture | Potential]** Same-name builder merge (`alignStoragePipeline` in two
  files, QG-1) means "the pipeline" is target-dependent with no single source of truth.
- **A3 [Architecture | Potential]** Duplicate analysis: alias analysis re-instantiated per
  pass/run (merge-vf :544; mark-stride-align alias state) instead of registered analyses.
- **A4 [Coverage | Confirmed-absence]** No discovered lit tests name the regbase
  builder pipelines; guard-combination matrix (enableFlatten × enableVfMergeLevel ×
  enableHIVMAutoStorageAlign) untested per combination.
- **A5 [Architecture | Potential]** Backend-specific logic (vsstb 512N+32, Fixpipe tables)
  hardcoded inside passes (mark dossier issue 3) — arch knowledge not in target-spec.

# Ordering-dependency summary table

| swapped pair | outcome |
|---|---|
| flatten ↔ mark-stride-align | silent wrong-axis marks (A1) |
| vf-fusion ↔ flatten | no-op degradation |
| flatten ↔ auto-vectorize-v2 | pass failure (safe) |
| enable-stride-align ↔ lowering | runtime misalignment, no compile error |
| merge-vf(L1) ↔ copy-insertion | merge becomes no-op |
