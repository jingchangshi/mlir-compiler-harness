# Architecture Status

Updated: 2026-09-05 (Phases 0–4 complete)

## Implemented

- Phase 0 contract: schema, query API v1, module boundaries, ADR-001..009.
- Phase 1 MVP engine: extractors (git / TableGen / C++ pass / pipeline+conditions / pattern /
  lit test), SQLite store, QueryService, CLI, incremental index (hash + indexer-version
  invalidation), fixture tests (7/7).
- Phase 2 validation on AscendNPU-IR: `validation-ascendnpu-ir.md`.
- Phase 3 agent-independent workflows (`docs/workflows/{repo-map,pass-analysis,pipeline-audit}.md`)
  and their real-repo execution on AscendNPU-IR:
  - `docs/compiler-architecture/` (repository/dialect/pipeline maps + pass catalog),
  - two full pass dossiers (`passes/hivm-flatten-ops.md`, `passes/hfusion-merge-vf.md`),
  - one pipeline audit (`pipelines/regbase-hivm-post-bufferization.md`) with 6 classified findings.
- Workflow-driven engine fixes (ADR-009): pattern base list, out-of-line runOnOperation
  containers, generated-base class bridging, cross-file dialect ownership, `modules --depth`.
  Result: 139 pattern links over 79 passes (≈0 before), 107 dialect-ownership edges, 5400 edges total.

## Validation of the core Phase-3 question

Deterministic facts were sufficient for all three workflows. Every dossier section was
fillable from queries + evidence-pointed files; repository-wide grep was not needed.
Two query/extractor gaps surfaced and were fixed (modules depth, pattern idioms); one
remains (`populate*` chasing) and did not block the workflows.


- Phase 4 agent adapters (`adapters/deepseek-harness/` goal templates + conventions,
  `adapters/zcode/` three thin skills) validated on AscendNPU-IR
  (`validation-adapters.md`): 9/9 fact consistency for a simulated capability-limited
  DeepSeek-style run vs the Phase 3 dossier; ZCode skills verified for frontmatter,
  harness resolution, no-rescan, and consistent output. Adapter contract recorded in
  ADR-010. Validation drove two contract fixes: multi-strategy pass-name resolution with
  explicit ambiguity, and `pipeline --brief`.

## Current limitations

- `populateXxxPatterns()` free-function chasing still missing (139/79 coverage, not 332/332).
- Pipeline detection is signature-based; some entry functions (e.g. `runRegBaseCompile`) missed.
- Op extraction covers direct defs and one-level multiclass aliases.
- Same-name factories across namespaces resolved by flagged locality heuristic (ADR-007).
- Test links are name/flag heuristics; `tests <pipeline>` often empty because RUN lines
  reference tool flags, not builder names.
- Short pass names may be inherently ambiguous across dialects (engine returns explicit
  ambiguity; agents must ask).
- No MCP, no agent skills, no clangd (deliberately deferred).

## Next recommended phase

See roadmap.md (adapter usage hardening / MCP decision deferred until hot-path evidence).
