# Architecture Status

Updated: 2026-09-05 (Phases 0–13 complete)

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

- Phase 8 Ascend ecosystem validation (ADR-014 + supplement, `docs/validation/phase8/`):
  harness migrated to triton-ascend (1255 files, 11 s, 0 diagnostics); six architecture
  docs; 4 pass dossiers (incl. the cross-repo annotation handoff); Python/C++ hybrid
  pipeline audit (make_ttgir) with three lowering frontiers and four hidden contracts;
  2 generic fixes; EG-1 (Python pipeline) recorded as the headline gap with design.

- Phase 9 cross-language provenance (ADR-015, `docs/validation/phase9/`): binding
  boundary entities + Python pipeline-composition functions (ast-based, signature
  detection) + full chain resolution; `pipeline-composition` query; pipeline-kind
  correctness (runOnOperation fix); triton-ascend 15 chains mapped; AscendNPU-IR
  regression clean.

- Phase 10 semantic boundary graph (ADR-016, `docs/validation/phase10/`):
  DIALECT_TRANSITIONS_TO edges (ConversionTarget-confirmed + pattern-ownership-inferred),
  attribute semantic roles (heuristic keyword table), boundary/dialect-transition/
  semantic-contract queries, workflow steps 7a + lens 1a; EG-2 closed.

- Phase 11 ecosystem handoff graph (ADR-017, `docs/validation/phase11/`): ecosystem
  layer derives dialect/op/attribute handoffs across the two repo indexes; 2 confirmed
  dialect handoffs (Annotation, HIVM), 10 op handoffs, 5 shared attribute contracts;
  `mlir-repomap ecosystem` query family; QG-7 closed at ecosystem level.

- Phase 12 intent & reasoning (ADR-018, `docs/validation/phase12/`): deterministic
  constraint extraction (177 on AscendNPU-IR, 171 pass-level), layered intent view
  (`pass-intent`), optimization opportunities as agent-layer dossier records;
  constraint substrate consumed by pass-analysis steps 7d/7e and pipeline-audit
  optimization-flow lens.

- Phase 13 review intelligence (ADR-019, `docs/validation/phase13/`): three-layer
  separation (graph facts / agent reasoning / evidence); Compiler Review Records for
  five passes with unguarded-invariant findings (merge-vf single-use assumption, AV2
  verifier completeness, annotation name validation, cross-dialect flatten contract);
  workflows 7f + lens 1x; no engine changes.

- Phase 14 knowledge evolution loop (ADR-020, `docs/validation/phase14/`): findings
  are doc-layer YAML artifacts with a validated lifecycle (open → … → resolved /
  rejected / superseded; every transition needs reason + evidence) and deterministic
  git drift tracking (`findings list|check|show`): commits touching evidence files
  since the baseline + snippet verification ("evidence changed"), report-only — never
  status-mutating. 7 findings seeded across both repos with regression-memory
  entries grounded in real commits; workflows gain pass-analysis step 0 (evolution
  check) + pipeline-audit lens 1e (risk delta); 25/25 tests.

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
- Findings: commit attribution is file-granular; `--since` needed when findings lack a
  recorded baseline; constraint line anchors can be off by one (snippet check tolerates).

## Next recommended phase

Attribute creator precision (RG-1) — see roadmap.md and ADR-020 (§8 of the phase 14
validation record).
