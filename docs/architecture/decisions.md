# Architecture Decision Log

## ADR-001 (2026-09-05, accepted) — TableGen-first pass modeling

Context: AscendNPU-IR has 219 pass defs in 18 Passes.td files but ~711 C++ files touching
PassWrapper; generated pass C++ creates duplicate entities and registration boilerplate.
Decision: the canonical `pass` identity is the TableGen pass argument (`Pass<"arg">`) when a
Passes.td def exists; C++-only passes (e.g. `bishengir-compile-regbase` with CMake-controlled
options) are identified by `getArgument()`. Generated headers/build artifacts are excluded
from the corpus; `.inc` includes are treated as build-time, not entities.
Alternatives: index generated C++ (rejected: duplicates, churn), C++-only (rejected: td is
the human source of truth).
Consequences: pass names in pipelines map via factory names `create<Name>Pass` ↔ td class
name; mismatches become `inferred` confidence.

## ADR-002 (2026-09-05, accepted) — Conditions are edge properties, not pipeline variants

Context: pipelines like the RegBase compile pipeline are heavily config-driven
(`if (config.getEnableHfusionCompile())`), with macro guards (`#if BISHENGIR_ENABLE_TORCH_CONVERSIONS`).
Decision: model conditional membership as PIPELINE_CONTAINS edges with a `condition` string +
`condition_kind` (config|macro), preserving guard text via brace tracking. Do not create
separate variant pipelines per config combination (combinatorial explosion; config object
shape differs per repo).
Consequences: `pipeline <name>` output can show which stages are optional and under what
guard; workflows reason about variants, the engine just reports guards.

## ADR-003 (2026-09-05, accepted) — Deterministic text/structural extraction, no LLM, clangd deferred

Decision: MVP uses regex + brace/scope tracking only; the semantic backend is a named
extension point (`SemanticBackend` interface reserved in design, not implemented). clangd
integration deferred until real validation shows structural extraction miss-rate justifies it
(build/compile_commands.json exists in AscendNPU-IR, so integration is feasible later).
Confidence levels keep the risk visible.

## ADR-004 (2026-09-05, accepted) — CLI is the primary adapter; MCP deferred to Phase 5

Decision: `mlir-repomap` CLI + Python API are the first and always-supported frontends.
MCP server is a thin wrapper over QueryService, added only after the query contract is
validated by real workflows. This guarantees DeepSeek-Harness-like shell-only agents retain
full capability.

## ADR-005 (2026-09-05, accepted) — Repository scoping

Decision: the engine indexes a configurable corpus (default: all tracked files minus
ignore-list). For mono-repos with vendored toolchains (AscendNPU-IR vendors llvm-project and
triton), a repo-specific `.mlir-repomap.toml` declares include/exclude globs. Generic
defaults exclude `third-party/`, `build/`, `third_party/`. This keeps the generic core model
clean while letting validation repositories bound cost.

## ADR-006 (2026-09-05, accepted) — `let constructor` is the authoritative pass↔factory link

Context: validation showed factory names do not follow the td class name (td class
`HIVMFlattenOps` ↔ `createFlattenOpsPass`). Name matching created wrong/duplicate entities.
Decision: Passes.td `let constructor = "ns::createXxxPass()"` is extracted as a confirmed
PASS_HAS_FACTORY edge; name-based matching is a fallback only. Confirmed during real-repo
validation. Alternatives: pure name matching (rejected: wrong links), clangd immediately
(deferred, ADR-003).

## ADR-007 (2026-09-05, accepted) — factory ambiguity is explicit, disambiguated by locality

Context: `createFlattenOpsPass` is defined in both `mlir::hfusion::` and `mlir::hivm::`;
unqualified call sites are textually ambiguous.
Decision: when several passes share one factory name, the resolver picks the candidate whose
definition file shares a path component with the call-site file ("same-dialect" heuristic)
and marks the edge `disambiguation: same-dialect-heuristic`. Exact resolution requires a
semantic backend and is the primary argument for investing in clangd integration later.
Alternatives: keep all candidates as multiple edges (rejected: false positives), pick first
silently (rejected: untraceable wrong data).

## ADR-008 (2026-09-05, accepted) — indexer version invalidates the parse cache

Context: incremental re-index only compares file hashes; changing extractor logic left stale
entities silently in the index (observed during validation).
Decision: `last_build.indexer_version` is stored in metadata; a mismatch forces full
re-extraction. Extractor logic changes must bump `INDEXER_VERSION` in model.py.

## ADR-009 (2026-09-05, accepted) — workflow-driven extractor refinements (Phase 3)

Context: executing the Phase 3 workflows on AscendNPU-IR exposed four real idioms the MVP
extractors missed, each blocking a dossier section: (a) `OpInterfaceRewritePattern` base not
recognized; (b) patterns registered in out-of-line `void X::runOnOperation()` bodies got no
PASS_USES_PATTERN link; (c) passes deriving from generated `impl::<TdClass>Base<>` had no
cpp-class→pass mapping; (d) dialect ownership failed when ops and dialect live in different
.td files (per-file resolution).
Decision: fix all four in the engine (generically, no repo-specific logic): extend the
pattern base list; treat out-of-line `runOnOperation|initialize|run` bodies as pattern-set
containers; bridge `impl::<TdClass>Base<Concrete>` via DEFINES props (`cpp_class` +
`impl_base`) to the td pass; resolve DIALECT_OWNS at graph-resolution time from node-id
prefixes and definition-directory names with `inferred` confidence. Also extend `modules`
to take `--depth` (workflow needed 2–3 levels; 1-level output was useless for this repo).
Evidence: PASS_USES_PATTERN edges 0→139 (79 distinct passes), DIALECT_OWNS 19→107,
hivm-flatten-ops dossier pattern section now complete. All changes keep AscendNPU-IR names
out of the core.
Alternatives: defer everything to clangd (rejected: these idioms are textual and cheap);
repo-specific heuristics (rejected by architecture principles).
Consequences: INDEXER_VERSION bumps (9); partial Phase 3.5 value delivered early.
Remaining known gap: `populateXxxPatterns()` free-function chasing still missing; clangd
still deferred (ADR-003) — re-evaluate after adapter phases.

## ADR-010 (2026-09-05, accepted) — Adapter contract: thin wrappers + explicit harness resolution

Context: Phase 4 built the first two adapters (DeepSeek Harness goal templates, ZCode
skills) and validated them on AscendNPU-IR.
Decision:
1. Adapters contain only trigger description, workflow entry, fixed query strategy, and
   output convention. Methodology is read at run time from `docs/workflows/` (source of
   truth); copying workflow text into an adapter is a violation.
2. Harness resolution order: `$MLIR_COMPILER_HARNESS` → `<target-repo>/../mlir-compiler-harness`
   → abort with a clear message. An agent must never substitute remembered methodology.
3. Goal templates open with an explicit guardrail block (read workflow first, RepoMap
   before source, no repo-wide grep, no name-guessing, evidence on every claim) because
   target models may vary in capability.
4. Ambiguous user input resolves to an explicit ambiguity error from the engine — the
   adapter instructs the agent to ask, never to pick silently (validated with "FlattenOps").
Evidence: validation-adapters.md — 9/9 fact consistency between an independent simulated
DeepSeek-style run and the Phase 3 dossier; ZCode skills trigger-resolve correctly.
Consequences: adapters stay small and safe to regenerate; engine/contract fixes during
validation (pass-name resolution, `pipeline --brief`) needed no adapter rewording.
