# Roadmap

done: Phase 0-13 (…, intent & optimization reasoning, compiler review intelligence
layer; ADR-001..019). Repos: AscendNPU-IR (baseline), triton-ascend (hybrid), ecosystem
layer over both.

current: none.

next (based on Phase 13 evidence):
1. **RG-1 attribute-creator tracing** (unchanged top candidate) — now also strengthens
   review records (creator-side ownership for the 5 ecosystem contracts).
2. **Unguarded-invariant watchlist**: the four Phase 13 findings are concrete
   engineering leads for the TARGET repos (merge-vf call-site guard, AV2 verifier
   inventory, annotation name validation, flatten axis-identity contract) — deliverable
   as issues/reports to the respective teams, which also validates the harness's
   practical value.
3. **EG-1 remainder / ecosystem persistence** (carried).

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
