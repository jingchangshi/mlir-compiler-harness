# Roadmap

done: Phase 0 (architecture contract), Phase 1 (RepoMap MVP), Phase 2 (AscendNPU-IR validation — report: validation-ascendnpu-ir.md).

current: none.

next (recommended order, re-evaluate after each):
1. **Phase 3 — agent-independent workflows** (`docs/workflows/repo-map.md`, `pass-analysis.md`,
   `pipeline-audit.md`), exercised end-to-end on AscendNPU-IR. Recommended next: the query
   contract now demonstrably carries the load (pass dossiers ≈1k tokens); the unvalidated
   risk is whether workflows produce good human architecture docs from it.
2. **Phase 3.5 — pattern-populate extraction**: chase `populateXxxPatterns(RewritePatternSet&)`
   helper functions to close the largest extraction gap (756 patterns with few pass links).
   This may be folded into Phase 3 findings or done with the clangd backend.
3. Phase 4 — ZCode adapter (3 thin skills) + DeepSeek Harness adapter (prompts + CLI conventions).

deferred:
- MCP server (Phase 5) — after workflows validate the contract.
- clangd/LSP semantic backend — the main fix for factory-namespace disambiguation (ADR-007)
  and pattern chasing; revisit after Phase 3.
- Ranking/PageRank, embeddings, Web UI.

rejected: indexing generated build-tree C++ (ADR-001); per-config pipeline variant nodes (ADR-002).
