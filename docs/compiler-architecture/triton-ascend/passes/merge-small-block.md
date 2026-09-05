# merge-small-block (MergeSmallBlockPass) — triton-ascend

> Provenance: Phase 8 validation, `pass-analysis` workflow. HEAD `8ba4ac4ce` · indexer v21
> · 2026-09-05. Primary file:
> `third_party/ascend/lib/DynamicCVPipeline/ComputeBlockOpt/MergeSmallBlockPass.cpp`
> (799 lines). C++-only pass (PassRegistration idiom, :368) — no TableGen def.

# Overview

Merges small compute blocks (≤ `MIN_VF_SIZE = 3` tensor compute ops) of the DynamicCV
pipeline into their operand/user block, reducing scheduling granularity on the cube/vector
units. Part of the ComputeBlockOpt optimization family.

# Pipeline Context

- Membership: `runOnOperation`-classified pipeline nodes (the ComputeBlockOpt driver
  `ComputeBlockOptPass.cpp` builds nested OpPassManagers inside its own `runOnOperation`,
  orders 12 and 23 in the extracted graph) — **extractor mislabel EG-1**: these are pass
  bodies, not named builders. The real pipeline is the ComputeBlockOpt internal sequence.
- Upstream invariant: blocks are CVPipeline `ComputeBlock`s with an id manager
  (`ComputeBlockIdManager`) and a `MemoryDependenceGraph` (MergeStrategy::Context :58-62).

# Registration

`PassRegistration<MergeSmallBlockPass> reg;` (:368); `getArgument() = "merge-small-block"`;
factory `createMergeSmallBlockPass` (cpppass-confirmed). No options beyond the constant.

# Input / Output Contract

- Input: module of compute blocks; "tensor compute op" classification
  (`isTensorComputeOp` :68-96: linalg non-copy/non-broadcast/non-const-fill, or
  Elementwise trait with tensor results; legacy function-name carve-out `pcb10_tc01_kernel`
  :73-77 — a hardcoded test-kernel special case, see issues).
- Output: fewer, larger blocks; block id manager updated; memory dependence preserved
  (uses `getAnalysis<AliasAnalysis>` :731 — a registered analysis, unlike AscendNPU-IR's
  ad-hoc alias state).

# Algorithm

cntComputeOps classifies block size; `MergeStrategy` (operand-side or user-side merge)
chooses direction using `MemoryDependenceGraph` + `id2order`; up/down block id sets guide
legal merges (:566, :619); cycle guard via seen-set (:713).

# Potential Issues

1. **[Maintainability | Confirmed]** `legacyFuncNames[]{"pcb10_tc01_kernel"}` (:73-77):
   a hardcoded kernel name changes pass semantics for a specific test function —
   test-driven production code path.
2. **[Architecture | Potential]** The ComputeBlockOpt family (7+ sibling passes) is
   C++-registered with no TableGen — invisible to td-based tooling; options travel via
   pipeline internals only.
3. **[Coverage | Potential]** `repo tests merge-small-block` → 0 linked tests (lit suite
   for ComputeBlockOpt lives under third_party/ascend/unittest as C++ gtest — test
   extractor gap for gtest-style coverage, EG-5).
