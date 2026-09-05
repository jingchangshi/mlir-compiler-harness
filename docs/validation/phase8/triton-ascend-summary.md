# triton-ascend Validation Summary

(Condensed; full records: architecture-validation.md, pass-analysis dossiers,
pipeline-audit/make-ttgir.md, extractor-gaps.md.)

- Index: 1255 files · 11 s · 1.5 MB · 8 dialects / 144 passes / 26 pipelines / 155
  patterns / 184 tests · **0 diagnostics**.
- Architecture docs: six, generated unmodified (docs/compiler-architecture/triton-ascend/).
- Pass dossiers: triton-to-linalg (lowering frontier), merge-small-block +
  tritongpu-accelerate-matmul (optimization, two idioms), triton-to-annotation
  (backend/attribute + cross-repo handoff into the bishengir annotation dialect).
- Pipeline audit: make_ttgir (Python) + init_triton_ascend_passes_ttir (C++) — builder
  provenance, three coexisting lowering frontiers, four hidden contracts.
- Engine changes: EG-4 fix (bare generated-base), factory suffix matching; EG-1/EG-2
  recorded with designs, not implemented.
