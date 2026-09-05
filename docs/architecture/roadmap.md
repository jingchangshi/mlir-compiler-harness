# Roadmap

done: Phase 0-8 (contract, engine, validation, workflows, adapters, deep validation,
provenance graph, provenance-aware workflows, Ascend ecosystem validation; ADR-001..014).
Repos validated: AscendNPU-IR (baseline), triton-ascend.

current: none.

next (based on Phase 8 evidence):
1. **EG-3 Python pipeline-composition extractor** (recommended next): ADD_PASS_WRAPPER
   bindings + Python stage lists — unlocks pipeline provenance for the entire Triton
   ecosystem side and connects triton-ascend's upstream path.
2. **EG-1 fix** (small): stop classifying runOnOperation bodies as pipeline builders.
3. **RG-1 attribute-creator tracing**: marker-construction call sites (upgrades
   CREATES_ATTRIBUTE beyond inferred; benefits both repos).

deferred: MCP, clangd, EG-5 gtest coverage, cross-repo handoff edges (QG-7) — none
blocking; revisit after EG-3.

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
