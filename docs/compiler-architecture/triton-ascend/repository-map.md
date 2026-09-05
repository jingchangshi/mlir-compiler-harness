# Repository Map — triton-ascend

HEAD `8ba4ac4ce`, 2026-09-05. Modules by extracted entity density (`repo modules --depth 3`):

| module | entities | role |
|---|---|---|
| `third_party/ascend/include` | 191 | Ascend backend TableGen (TritonToLinalg, TritonToLLVM, TritonToStructured Passes.td) + headers |
| `third_party/ascend/unittest` | 186 | C++ gtest for the Ascend backend |
| `include/triton/Dialect` | 183 | upstream Triton dialect TableGen (Triton/TritonGPU/TritonNvidiaGPU/Gluon/Instrument) |
| `third_party/ascend/lib` | 178 | Ascend backend passes/pipelines (DynamicCVPipeline, TritonToLinalg) |
| `lib/Dialect/TritonGPU` | 51 | TTGIR transforms (incl. upstream AccelerateMatmul) |
| `lib/Conversion/TritonToTritonGPU` | 31 | TTIR → TTGIR conversion |
| `lib/Dialect/TritonNvidiaGPU` | 28 | NVIDIA-specific dialect (kept in the fork) |
| `third_party/ascend/costmodel` | 26 | Ascend cost model |
| `lib/Conversion/TritonGPUToLLVM` | 19 | TTGIR → LLVM lowering |
| `lib/Dialect/Triton` | 16 | TTIR ops/transforms |

## Key structural facts

- **Two compilation stacks coexist**: the upstream Triton→TTGIR→LLVM path
  (`lib/Conversion/...`) and the Ascend path **Triton → Linalg → AscendNPU-IR**
  (`third_party/ascend/lib/TritonToLinalg/`, dialect `triton_ascend`).
- The Ascend NPU-IR lives in the *nested* `third_party/ascend/AscendNPU-IR/` checkout —
  excluded from the corpus (it is the Phase 2–7 baseline repository, indexed separately).
- Pipeline registration idioms are mixed (see pipeline-map.md): td passes with
  `let constructor`, C++ `PassRegistration` (ComputeBlockOpt family), and **Python-side
  composition** via `python/src/passes.cc` `ADD_PASS_WRAPPER` bindings (outside the C++
  corpus — extractor gap EG-3).
