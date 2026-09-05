# Roadmap

done: Phase 0 (contract) · Phase 1 (MVP engine) · Phase 2 (validation) · Phase 3
(workflows; ADR-009) · Phase 4 (agent adapters; ADR-010) · Phase 5 (ZCode-driven deep
analysis validation; ADR-011, docs/validation/phase5/).

current: none.

next (ranked by Phase 5 observed friction — ADR-011):
1. **C. Pattern & pipeline identity extraction enhancement** (was Phase 3.5, promoted):
   chase free-function `populate*Patterns` registration (QG-3, affected 6/6 analyses) and
   qualify same-name pipeline builders (QG-1, produced a wrong-by-merge stage list on the
   first real audit).
2. **D. Schema enhancement**: attribute entities + REFERENCES edges (QG-4), test feature
   tags & pipeline links (QG-5), cross-scope `seq` ordering (QG-6).
3. **E. Workflow refinements**: fold WG-1..5 into docs/workflows (cheap doc changes).

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
