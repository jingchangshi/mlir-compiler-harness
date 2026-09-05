# Repository Selection

Chosen: triton-lang/triton-ascend (local clone `/home/shijingchang/workspace/triton-ascend`,
HEAD `8ba4ac4ce`).

Rationale: it complements the AscendNPU-IR baseline — Triton frontend, TTIR/TTGIR/LLVM
lowering, and the Ascend Triton→Linalg→NPU-IR path; together the two repos cover the
Ascend AI compiler stack (frontend → MLIR mid-end → backend IR → hardware).

Corpus scoping (`.mlir-repomap.toml`, ADR-005): include `lib/`, `include/`,
`third_party/ascend/`; exclude the **nested baseline checkout**
`third_party/ascend/AscendNPU-IR/` (indexed separately as the baseline), other vendors'
backends (nvidia/amd/proton/f2reduce), `build/`, `bin/`. Result: 1255 files, 11 s, 1.5 MB,
0 diagnostics. `compile_commands.json` exists at repo root (clangd-ready if ever needed).
