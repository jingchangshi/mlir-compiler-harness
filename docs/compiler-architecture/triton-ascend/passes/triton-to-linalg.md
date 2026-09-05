# triton-to-linalg (TritonToLinalg) — triton-ascend

> Provenance: Phase 8 ZCode-driven validation, `pass-analysis` workflow (provenance-aware).
> triton-ascend HEAD `8ba4ac4ce` · indexer v21 · 2026-09-05.
> Primary files: `third_party/ascend/lib/TritonToLinalg/TritonToLinalgPass.cpp` (2319 lines),
> `third_party/ascend/include/TritonToLinalg/Passes.td:5`, tests 46 linked.

# Overview

The Ascend path's **frontier pass**: converts Triton (TTIR) into Linalg + triton_ascend ops,
handing the kernel over to the Linalg-based AscendNPU-IR compilation stack. This is the
abstraction boundary where Triton-level semantics (block pointers, descriptors, SIMT/SIMD
modes) are lowered into the representation the Phase 2–7 baseline repo consumes.

# Pipeline Context

- `init_triton_ascend_passes_ttir`, order 5, module scope — the Ascend TTIR-level pass
  registration function (builder at `third_party/ascend/triton_ascend.cc:62`, confirmed).
- Upstream invariant: Triton IR with tensor-descriptor metadata validated *before* any
  mutation (`validatePointerDescriptorHandoffMetadata`, TritonToLinalgPass.cpp:1688-1693).
- Downstream: Linalg/hfusion ops consumed by the AscendNPU-IR stack (`hfusion::Conv*Op`
  mentions in the cube check, :1700-1707 — the handoff contract is type-level).

# Registration

`def TritonToLinalg : Pass<"triton-to-linalg", "mlir::ModuleOp">` with six options
(globalKernel, namedOps, enableNd2nzOnVector, enableSelectAnalysis, compileOn91095,
compileMode simd/simd_simt_template/simt_only) — Passes.td:5-27; factory
`triton::createTritonToLinalgPass()` confirmed via `repo pass`.

# Input / Output Contract

- Input: triton.func kernels; descriptor handoff metadata must validate first (else
  signalPassFailure).
- Output: linalg + `triton::ascend` + hfusion ops; kernel classification attributes
  (pure-AIV vs mix-CV) decided inside (existDot walk, :1697-1707).
- Hidden cross-pass state: `existDotFlag`/`existSIMTOp` member flags — and a documented
  **ordering hazard** (comment :1712-1720): SIMT detection must run *after*
  `processStridedLoadStoreRewriteOperations` (which materializes IndirectLoad/Store);
  misordering mislabels parallel_mode → no localMemorySize reserved → **runtime VEC
  out-of-bounds (error 341)**. This is a self-contained ordering contract the pipeline
  must respect (the pass orders it internally — defensive, but the comment shows the
  failure mode).

# Algorithm

runOnOperation (:1676+): mode parse → descriptor handoff validation → cube-op detection →
descriptor ops conversion → implicit-permute → SIMT indirect-load fast-path →
block/loop conversion into linalg (multiple-block control flow handled at :929) with
per-dialect converters (TTOpConverters, LoadStoreConverter). Canonicalization patterns
populated via `populateTritonToLinalgCanonicalizationPatterns` (:1333-1403, ~10 pattern
families) — provenance: `repo pattern-owner FoldScanOffsetAddPtrChain` resolves to
`pass:triton-to-linalg` (call site + definition evidence).

# IR Examples

46 linked lit tests (`third_party/ascend/test/...triton_to_linalg...`), e.g. descriptor
load/store conversions with CHECK lines on linalg.generic outputs; before/after pairs
available in tests (workflow convention: lit CHECK lines are the deterministic source).

# Supported / Unsupported

Supported: descriptor ops, implicit permute, SIMT indirect fast-path, three compile modes.
Unsupported/limited: mode string is parsed at runtime — invalid `compile-mode` fails the
pass (correct-by-error); pure-AIV vs mix-CV classification drives downstream template
selection (not a rejection, but a hard semantic fork).

# Potential Issues

1. **[Correctness | Highly Likely]** The SIMT-detection ordering comment (:1712-1720)
   documents a real production failure (error 341) whose prevention is *internal ordering
   discipline* — no verifier asserts the materialization happened before classification.
   Pipeline reorderings of the internal steps would silently regress.
2. **[Architecture | Potential]** The pass is a 2319-line monolith containing ≥3
   sub-analyses (descriptor, permute, SIMT fast-path) + 2 pattern populate functions —
   responsibility concentration; the Phase-5-style audit lens would flag it.
3. **[Coverage | Potential]** 46 tests cover the flow, but the comment-documented
   error-341 scenario has no named test found via `repo tests`.
