# Phase 8 Validation — Ascend Compiler Ecosystem Generalization

Date: 2026-09-05 · triton-ascend HEAD `8ba4ac4ce` · AscendNPU-IR HEAD `5671889a3` ·
indexer v21 · harness tests 12/12.

Question of the phase: **do the graph + workflows survive across Ascend compiler
architectures** (C++ MLIR compiler vs Python/C++ hybrid pipeline)?

Layout:

```
repository-selection.md    why triton-ascend, corpus scoping
architecture-validation.md repo-map execution + extractor coverage per goal §4-6
pass-analysis/             triton-to-linalg (lowering) · merge-small-block +
                           tritongpu-accelerate-matmul (optimization, 2 idioms) ·
                           triton-to-annotation (backend/attribute + cross-repo handoff)
                           (full dossiers under docs/compiler-architecture/triton-ascend/passes/)
pipeline-audit/make-ttgir.md   Python/C++ hybrid pipeline audit
query-gaps.md              QG-7 cross-repo handoff, QG-8 gtest links
extractor-gaps.md          EG-1 Python pipeline · EG-2 dialect-transition edge ·
                           EG-3 registration idioms (+ fixed EG-4/EG-5-renumbered items)
generalization-report.md   verdict + schema decision + next phase
comparison.md / ascendnpu-ir-summary.md / triton-ascend-summary.md (earlier records)
```

Headline: **0 diagnostics, all provenance queries working cross-repo after two small
generic fixes; the Ascend flow's authoritative builder is Python (`backend/compiler.py`
`make_ttgir`), which the graph does not yet model (EG-1) — audits read the stage lists
alongside the graph.**
