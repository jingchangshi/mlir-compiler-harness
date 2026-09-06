# Roadmap

done: Phase 0-16 (…, attribute creator precision, semantic finding impact analysis;
ADR-001..022). Repos: AscendNPU-IR (baseline), triton-ascend (hybrid), ecosystem layer
over both.

current: none.

next (based on Phase 16 evidence):
1. **Review-scope watchlist delivery**: the impact reports for the 7 seeded findings
   are concrete review leads for the target repos' teams (as Phase 13's unguarded
   invariants were) — package as deliverables, which also validates practical value.
2. **EG-1 remainder / ecosystem persistence** (carried).
3. C++-level attribute definitions (attrs without td AttrDef) still surface only as a
   diagnostic; gtest linking is name-level only (stage 1).

deferred (unchanged): MCP, clangd, runtime contract graph, attribute value semantics.

deferred (unchanged): MCP, clangd, runtime contract graph, attribute value semantics —
the intent/constraint layer reduced the pressure for all of them.

deferred (unchanged): MCP, clangd, runtime contract graph, attribute value semantics.

deferred (unchanged): MCP, clangd, attribute value semantics, full interpreter.

deferred (unchanged): MCP, clangd, gtest coverage extraction, cross-repo handoff
declarations (QG-7) — none blocking; the ecosystem now spans two repos with provenance.

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
