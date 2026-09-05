# Roadmap

done: Phase 0-12 (…, cross-repository handoff graph, intent & optimization reasoning;
ADR-001..018). Repos: AscendNPU-IR (baseline), triton-ascend (hybrid), ecosystem layer
over both.

current: none.

next (based on Phase 12 evidence):
1. **RG-1 attribute-creator tracing** (promoted): marker-construction call sites —
   completes attribute contracts (ecosystem + semantic layers both consume it).
2. **Constraint equivalence classes** (small): group per-occurrence constraints by
   condition semantics to power cross-pass reasoning.
3. **EG-1 remainder** (carried): Python stage lists as first-class pipeline nodes.

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
