# Phase 8 Query Gaps

- QG-7 — Cross-repo handoff contract: `triton-to-linalg` emits hfusion ops consumed by the
  AscendNPU-IR stack, but the two indexes are separate; no query answers "which dialect
  boundary does this repo feed". Impact: ecosystem-level audits need manual joining.
  Fix direction: corpus-level `external_dialect` declarations (repo config) + edges from
  passes to external dialect ops by type name. Priority: Low-Medium (only matters for
  multi-repo audits).
- QG-8 — `tests` for C++ gtest files returns feature tags but no pass links (EG-5 below
  the query level). Priority: Medium.
- No other query shortfalls: pattern-owner / pipeline-builder / attribute worked
  unchanged on the new repo.
