# Phase 8 Query Gaps

- **QG-7 — cross-repo handoff contract**: `triton-to-annotation` forwards attributes into
  the bishengir annotation dialect consumed by the baseline repo's stride-align machinery;
  `triton_to_hivm`/`triton_to_hfusion` hand the IR to the baseline stack. The two indexes
  are separate by design, so no query answers "which dialect boundary does this repo feed
  and who consumes it". Fix direction: `external_dialect` declarations in repo config +
  edges from passes to external dialect type names. Priority: Low-Medium (first real need
  appeared this phase; no workflow blocked).
- **QG-8 — gtest files carry feature tags but no TEST_COVERS_PASS links** (third_party/
  ascend/unittest). Priority: Medium.
- No other gaps: pattern-owner / pipeline-builder / attribute / tests all worked
  unchanged on the new repository.
