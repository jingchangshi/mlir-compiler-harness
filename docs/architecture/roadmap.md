# Roadmap

done: Phase 0-9 (contract, engine, validation, workflows, adapters, deep validation,
provenance graph, provenance-aware workflows, ecosystem validation, cross-language
provenance; ADR-001..015). Repos validated: AscendNPU-IR (baseline), triton-ascend
(C++ + Python hybrid).

current: none.

next (based on Phase 9 evidence):
1. **Dialect-transition edges (EG-2 promotion candidate)**: with cross-language chains
   in place, the triton→HIVM/HFusion handoff is now the visible frontier; a
   DIALECT_TRANSITIONS edge (from pass input/output op ownership) would make ecosystem
   audits queryable — requires a consuming workflow first (pass-analysis dialect
   transition step).
2. **RG-1 attribute-creator tracing**: marker-construction call sites (setAttr /
   createAlignMarkOp) — both repos benefit.
3. **pm.run stage markers as edges**: turn composition-function pm.run calls into
   per-stage verification boundaries.

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
