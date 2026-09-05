# Dialect Map — triton-ascend

From `repo dialects` (HEAD `8ba4ac4ce`, 2026-09-05):

| Dialect | definition | owned ops | notes |
|---|---|---|---|
| Triton | `include/triton/Dialect/Triton/IR/TritonDialect.td` | 50 | TTIR core (upstream style: direct `Op<Triton_Dialect,...>`) |
| TritonGPU | `.../TritonGPUDialect.td` | 23 (+1 attr) | TTGIR |
| TritonNvidiaGPU | `.../TritonNvidiaGPUDialect.td` | 28 (+3 attrs) | NVIDIA-specific (fork keeps it) |
| TritonAscend | `third_party/ascend/include/.../TritonAscendDialect.td` | 16 | **Ascend-specific ops** (IndirectLoad/Store, Dot, ...) |
| TritonInstrument | upstream | 5 | |
| Gluon | upstream | 1 (+2 attrs) | |
| AscendModel / Triton_Structured | `third_party/ascend` | 0 indexed | helper dialects; ops via multi-level multiclass (caveat) |

Compared with AscendNPU-IR (13 dialects, ownership via `Xxx_Op` multiclass aliases), the
upstream side uses direct `Op<Dialect,...>` defs — cross-file ownership resolution covers
both styles (DIALECT_OWNS inferred edges).
