# Roadmap

done: Phase 0 (contract) · Phase 1 (MVP engine) · Phase 2 (validation) · Phase 3
(workflows; ADR-009) · Phase 4 (agent adapters; ADR-010) · Phase 5 (deep validation;
ADR-011) · Phase 6 (provenance-aware graph; ADR-012, docs/validation/phase6/).

current: none.

next (based on Phase 6 evidence):
1. **Workflow refinements** (fold WG-1..5 + provenance-query guidance into docs/workflows):
   the graph now answers questions the workflows don't yet instruct agents to ask
   (`pattern-owner`, `attribute`).
2. **Multi-repo adapter hardening**: run DeepSeek/ZCode adapters on a second MLIR repo to
   prove the provenance graph is not AscendNPU-IR-shaped.

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
