# Roadmap

done: Phase 0 (contract) · Phase 1 (MVP engine) · Phase 2 (AscendNPU-IR validation) ·
Phase 3 (agent-independent workflows + real-repo execution; engine refinements per ADR-009).

current: none.

next (recommended, based on Phase 3 evidence — re-evaluate after each):
1. **Phase 4 — agent adapters** (recommended next). Rationale: the workflows and query
   contract have now been proven end-to-end by an agent following them; the marginal value
   is in letting other agents (ZCode skills, DeepSeek Harness prompts) reproduce that
   behavior with near-zero methodology drift. Both adapters are thin wrappers —
   `adapters/zcode/` (3 skills referencing docs/workflows/) and `adapters/deepseek-harness/`
   (goal/system prompt templates + CLI conventions).
2. **Phase 3.5 (background, small) — `populateXxxPatterns` chasing**: a single helper-level
   extractor (find `populate\w+Patterns(RewritePatternSet&)` definitions and their call
   sites within pass classes) would lift pattern-link coverage from 79/332 toward the
   long tail. Defer until a real analysis is blocked by it — Phase 3 showed the workflows
   tolerate the gap.
3. Phase 5 — MCP adapter (only after adapters show which commands are hot).

deferred:
- clangd/LSP semantic backend — ADR-007 factory-namespace disambiguation is the only
  confirmed consumer; the flagged locality heuristic held up in Phase 3. Revisit if dossiers
  start contradicting the graph.
- Ranking/PageRank, embeddings, Web UI.

rejected: indexing generated build-tree C++ (ADR-001); per-config pipeline variant nodes (ADR-002).
