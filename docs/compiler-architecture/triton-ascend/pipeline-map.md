# Pipeline Map — triton-ascend

From `repo pipelines` (26 pipelines; top by stage count):

| stages | pipeline | file |
|---|---|---|
| 25 | runOnOperation (ComputeBlockOpt driver) | ComputeBlockOptPass.cpp |
| 15 | init_triton_ascend_passes_ttir | triton_ascend.cc |
| 10 | runOnOperation (AddDynamicCVPipeline) | AddDynamicCVPipeline.cpp |
| 7 | runOnOperation (SplitDataflow) | SplitDataflow.cpp |
| 6 | registerAscendModelPipeline | PassRegistration.cpp |
| 5 | runOnOperation (TritonToLinalgPass) | TritonToLinalgPass.cpp |

## Idioms (validated via pipeline-builder queries)

1. **td passes with `let constructor`** (Ascend side, e.g. `triton-to-linalg`) —
   identical to AscendNPU-IR; factory links confirmed.
2. **C++ `PassRegistration`** (ComputeBlockOpt family: merge-small-block,
   unify-alloc-block, ...) — cpp-only passes via `getArgument()`; no td def.
3. **Python-side composition**: `python/src/passes.cc` wraps passes with
   `ADD_PASS_WRAPPER_0("add_accelerate_matmul", createTritonGPUAccelerateMatmul)`; the
   actual TTGIR optimization pipeline is composed in Python compiler stages, invisible to
   C++ extraction (**EG-3**).
4. `runOnOperation`-classified "pipelines": pass bodies that internally build
   OpPassManagers (ComputeBlockOpt driver) get pipeline nodes (**EG-1** mislabel — they
   are pass implementations, not named builders).

## Abstraction boundary

`triton-to-linalg` (order 5 of `init_triton_ascend_passes_ttir`) is where the Triton
abstraction drops to Linalg → the flow then hands over to the AscendNPU-IR stack (the
Phase 2–7 baseline). The upstream TTGIR→LLVM path bypasses Linalg entirely — two lowering
frontiers coexist in one repo.
