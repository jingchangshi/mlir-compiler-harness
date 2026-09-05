# Pass Catalog — triton-ascend

From `repo passes` (HEAD `8ba4ac4ce`): 144 passes total.
Distribution: `third_party/ascend/include` 50 (TableGen defs), `include/triton` 48,
`third_party/ascend/lib` + costmodel ~14 (C++-only PassRegistration family), remainder
upstream transforms/headers.

## Registration idioms observed

- td + `let constructor` (Ascend passes) — factory confirmed via query.
- td WITHOUT `let constructor` (upstream Triton) — factory intentionally absent
  (create* generated at build time, ADR-001); pattern chains still resolve.
- C++ `PassRegistration` (ComputeBlockOpt) — cpp-only pass nodes.

## Per-pass dossiers (Phase 8 validation)

- `passes/triton-to-linalg.md` (lowering, Ascend path)
- `passes/merge-small-block.md` (optimization, ComputeBlockOpt)
- `passes/tritongpu-accelerate-matmul.md` (upstream-idiom optimization)
