# AscendNPU-IR — Baseline Summary (Phases 2-7)

Validated baseline: 2951 files · 13 dialects · 332 passes · 62 pipelines · 155→756
patterns (raw) with provenance chains · 5400+ edges · 0 diagnostics.

Coverage of the AscendNPU-IR half of the stack: HFusion/HIVM fusion & vectorization,
memory/layout (stride-align family), bufferization, RegBase backend flow, phased
decomposition. Provenance surface: pipeline identity (file-qualified), pattern population
chains, attribute contracts, seq ordering, test feature tags.

Key artifacts: docs/compiler-architecture/ (6 maps + 8 pass dossiers + pipeline audits),
docs/validation/phase5..7/.
