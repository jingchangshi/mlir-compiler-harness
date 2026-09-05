# Architecture Status

Updated: 2026-09-05 (Phases 0–8 complete)

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

- Phase 5 ZCode-driven deep validation on AscendNPU-IR (`docs/validation/phase5/`):
  six expert-level pass dossiers (MergeVecScope, HFusionFlattenOps, MarkStrideAlign,
  EnableStrideAlign, AutoVectorizeV2, VFFusion) + a regbase contract/ordering/abstraction
  audit, all produced through the ZCode skills. Outcome: no hard blockers; gaps logged
  (QG-1..6, WG-1..5) and ranked in ADR-011.

- Phase 6 provenance-aware graph (ADR-012, `docs/validation/phase6/`): pipeline
  identity = file-qualified (dual `alignStoragePipeline` unmerged); pattern-population
  chains by signature (FlattenOps heuristic→confirmed); attribute entities
  (StrideAlignDimsAttr chain = one query); `seq` ordering; test feature tags. New
  queries: `pattern-owner`, `pipeline-builder`, `attribute`.

- Phase 7 provenance-aware workflow intelligence (ADR-013, `docs/validation/phase7/`):
  workflows mandate pattern-owner/attribute/pipeline-builder; provenance maps generated
  (pattern-map.md, attribute-map.md); regbase audit re-run with builder chains and swap
  outcomes; no new query type needed.

- Phase 8 Ascend ecosystem validation (ADR-014, `docs/validation/phase8/`): harness
  migrated to triton-ascend (1255 files, 11 s, 0 diagnostics); six architecture docs
  generated; 3 pass dossiers incl. the upstream-idiom probe; 2 generic fixes (bare
  generated-base EG-4, factory suffix matching); gaps EG-1/3/5 recorded with designs.

## Current limitations

- Pattern-set chains stop at helpers not taking `RewritePatternSet&`; attribute provenance
  is name-level (no per-op attachment).
- Triton-ecosystem gaps: Python-composed pipelines invisible (EG-3), runOnOperation
  pipeline mislabel (EG-1), gtest coverage not extracted (EG-5) — designs recorded.
- Pipeline detection is signature-based; some entry functions (e.g. `runRegBaseCompile`) missed.
- Op extraction covers direct defs and one-level multiclass aliases.
- Same-name factories across namespaces resolved by flagged locality heuristic (ADR-007).
- Test links are name/flag heuristics; `tests <pipeline>` often empty because RUN lines
  reference tool flags, not builder names.
- Short pass names may be inherently ambiguous across dialects (engine returns explicit
  ambiguity; agents must ask).
- No MCP, no agent skills, no clangd (deliberately deferred).

## Next recommended phase

Pattern extraction enhancement (QG-3 populate*-chasing + QG-1 pipeline identity) — see
roadmap.md and ADR-011.
