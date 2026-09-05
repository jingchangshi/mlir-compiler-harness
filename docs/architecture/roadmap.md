# Roadmap

done: Phase 0 (contract) · Phase 1 (MVP engine) · Phase 2 (AscendNPU-IR validation) ·
Phase 3 (workflows + real-repo execution; ADR-009) · Phase 4 (agent adapters, validated;
ADR-010, validation-adapters.md).

current: none.

next (recommended, based on Phase 4 evidence — re-evaluate after each):
1. **Adapter usage hardening** (recommended next): run the DeepSeek Harness templates and
   ZCode skills on real tasks across ≥2 different models and ≥2 more MLIR repos; collect
   the run reports' "missing/insufficient query" lines as the evidence channel that should
   drive the next engine/contract investment.
2. **Phase 3.5 (background, small) — `populateXxxPatterns` chasing**: unchanged from
   Phase 3 assessment; still no validation run was blocked by it.
3. **MCP adapter**: still deferred. Phase 4 runs surfaced no CLI-inconvenience pressure;
   decide after the usage-hardening loop.

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
