# Roadmap

done: Phase 0-7 (contract, engine, validation, workflows, adapters, deep validation,
provenance graph, provenance-aware workflows; ADR-001..013).

current: none.

next (based on Phase 7 evidence):
1. **Second MLIR repository validation** (recommended next): Phase 7 proved the workflow
   layer on AscendNPU-IR; the untested risk is AscendNPU-IR-shaped extraction. A second
   repo (e.g. an upstream-MLIR-based compiler or triton fork) would exercise the generic
   core against different idioms — the same move that made Phases 2/5 decisive here.
2. **RG-1 attribute-creator tracing** (small): marker-construction call-site extractor
   (setAttr/createAlignMarkOp paths) to upgrade CREATES_ATTRIBUTE beyond inferred.

deferred (unchanged): MCP — no hot-path pressure through Phase 7; clangd — no wrong-fact
incident through Phase 7; attribute value semantics — RG-1 does not require it yet.

deferred (unchanged, evidence-based): MCP — no hot-path pressure through Phase 6; clangd —
no wrong-fact incident through Phase 6; the remaining name-level attribute semantics and
non-RewritePatternSet indirection do not yet justify a full semantic backend.

deferred (evidence-based):
- **A. MCP adapter** — no CLI-inconvenience pressure in Phases 4–5.
- **B. clangd backend** — no wrong-fact incident in Phases 3–5; the flagged heuristics held.
- Multi-repo adapter hardening — after the extraction fixes above, so new repos are
  onboarded against the improved baseline.

deferred:
- clangd/LSP semantic backend — no wrong-fact incident in Phase 3/4 validations;
  the flagged locality heuristic held. Revisit only if a dossier contradicts the graph.
- Ranking/PageRank, embeddings, Web UI.

rejected: indexing generated build-tree C++ (ADR-001); per-config pipeline variant nodes (ADR-002);
methodology duplication inside adapters (ADR-010).

deferred:
- clangd/LSP semantic backend — ADR-007 factory-namespace disambiguation is the only
  confirmed consumer; the flagged locality heuristic held up in Phase 3. Revisit if dossiers
  start contradicting the graph.
- Ranking/PageRank, embeddings, Web UI.

rejected: indexing generated build-tree C++ (ADR-001); per-config pipeline variant nodes (ADR-002).
