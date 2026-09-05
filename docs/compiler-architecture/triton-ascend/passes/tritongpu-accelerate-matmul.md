# tritongpu-accelerate-matmul (TritonGPUAccelerateMatmul) — triton-ascend

> Provenance: Phase 8 validation, upstream-idiom case. HEAD `8ba4ac4ce` · indexer v21.
> Primary files: `include/triton/Dialect/TritonGPU/Transforms/Passes.td:202`,
> `lib/Dialect/TritonGPU/Transforms/AccelerateMatmul.cpp` (class :984, generated base
> `TritonGPUAccelerateMatmulBase`).

# Overview

Upstream Triton TTGIR optimization: rewrites matmul-like ops into MMA layouts
(BlockedToMMA family). Included in Phase 8 deliberately as the **upstream-idiom probe**.

# Provenance findings (the point of this dossier)

- td def has **no `let constructor`** — the create* function is generated at build time;
  `repo pass tritongpu-accelerate-matmul` therefore reports `factory: []`
  (correct-by-ADR-001; instantiation happens via generated headers +
  `python/src/passes.cc` `ADD_PASS_WRAPPER`).
- **Pattern provenance works without any triton-specific code**: 4 direct
  PASS_USES_PATTERN edges (BlockedToMMA, BlockedToMMAv5, ScaledBlockedToMMA,
  ScaledBlockedToMMAv5 — confirmed) + 1 populator chain (inferred).
- Pipeline membership: none in the C++ corpus — the pass is composed **in Python** stages
  (EG-3); `python/src/passes.cc:71` is the only in-corpus reference outside its own file.
- Cross-repo class idiom: pass class declared in a header inheriting a bare
  (non-`impl::`) generated base — fixed generically in Phase 8 (EG-4) and re-validated on
  both repos.

# Takeaway

The generic engine handles the upstream Triton idiom with zero repo-specific code, except
for two consciously deferred gaps: Python-side pipeline composition (EG-3) and gtest-style
test coverage (EG-5).
