# Architecture Status

Updated: 2026-09-05 (Phases 0–2 complete)

## Implemented

- Phase 0 contract: entity/edge/evidence schema, stable query API v1, module boundaries, ADR-001..008.
- Phase 1 MVP engine (`repomap/`): git facts, TableGen structural extractor (dialect/op/pass
  incl. `let constructor`), C++ pass extractor, pipeline extractor with conditions & nesting,
  pattern extractor, lit test extractor, SQLite store, QueryService, `mlir-repomap` CLI,
  incremental re-index (hash + indexer-version invalidation), synthetic fixture tests (7/7).
- Phase 2 real-repo validation on AscendNPU-IR: see `validation-ascendnpu-ir.md`.
  364 passes, 13 dialects, 62 pipelines, 756 patterns, 953 tests, 576 pipeline memberships,
  15 s full index, 0 parse diagnostics.

## Current limitations

- Pattern→pass links via `populateXxxPatterns()` helper functions are not chased (largest gap).
- Pipelines are detected by signature pattern; some entry points (`runRegBaseCompile`) missed.
- Op extraction covers direct and one-level multiclass aliases only.
- Same-name factories across namespaces resolved by a flagged locality heuristic (ADR-007).
- Test coverage is name/flag matching (heuristic); no CHECK-body interpretation.
- No MCP, no agent skills, no clangd yet (deliberately deferred).

## Next recommended phase

Phase 3 (agent-independent workflows) — see roadmap.md.
