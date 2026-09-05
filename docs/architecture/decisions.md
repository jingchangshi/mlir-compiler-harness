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

## ADR-011 (2026-09-05, accepted) — Phase 5 outcome: gaps recorded, not implemented; next investment ranked by observed friction

Context: Phase 5 ran six expert-level pass analyses and one pipeline audit through the
ZCode adapter. Three recurring gaps were observed (see docs/validation/phase5/query-gaps.md):
free-function `populate*` pattern ownership (6/6 analyses affected, QG-3, High);
same-name pipeline builder merge (QG-1, High); attribute-level producer/consumer queries
(QG-4, Medium). No analysis was hard-blocked, and no wrong fact was produced by the graph.
Decision: record gaps instead of implementing (per Phase 5 rules). Rank next-phase
candidates by observed friction: C (pattern extraction enhancement = QG-3/QG-1 fixes)
first; then D (schema enhancement: attr entities from QG-4 + test feature tags from QG-5);
MCP (A) and clangd (B) remain deferred — no hot-path pressure and no wrong-fact incident
were observed.
Consequences: the engine stays frozen at Phase 4 while its gap log carries the next
phase's backlog; workflow gaps (WG-1..5) are cheap doc changes to fold into the next phase.

## ADR-012 (2026-09-05, accepted) — Provenance-aware graph: pipeline identity + pattern population chain

Context: Phase 5 proved the main limitation was missing deterministic provenance (QG-1,
QG-3 among others). 
Decision:
1. Pipeline identity is `pipeline:<file>:<name>` (namespace+file+function), never the bare
   name; bare-name queries resolve uniquely or return explicit ambiguity. Builders are
   first-class `function` nodes (PIPELINE_BUILT_BY). Validated on AscendNPU-IR's dual
   `alignStoragePipeline`.
2. Pattern-population functions are identified by their signature (a `RewritePatternSet&`
   parameter), not by naming convention; the `populate*` prefix is used only for cross-file
   call-site markers. Chain: PASS_USES_PATTERN_POPULATOR -> FUNCTION_CALLS* ->
   FUNCTION_DEFINES_PATTERN, all with file:line evidence and confirmed/inferred confidence.
3. Attribute provenance: `attribute:<Name>` nodes from `<Name>Attr::name` references;
   pass-body references become CREATES_ATTRIBUTE (inferred); file references stay
   REFERENCES (heuristic).
4. Class-name collisions across dialects (two `FlattenOpsPass`) are resolved at edge-rewrite
   time by the same-dialect locality heuristic (extension of ADR-007), flagged in props.
5. `seq` (monotonic source order) added next to per-scope `order` (QG-6); test feature tags
   added as heuristic node summaries (QG-5).
Evidence: docs/validation/phase6/README.md — FlattenOps ownership heuristic→confirmed,
alignStoragePipeline merge eliminated, StrideAlignDimsAttr chain a single query.
Consequences: query API gains `pattern-owner`, `pipeline-builder`, `attribute` (all with
workflow consumers from Phase 5 dossiers); INDEXER_VERSION bumps force one full re-index.
Remaining: value-level attribute semantics and non-RewritePatternSet builder indirection
stay unmodeled (documented, low impact).

## ADR-013 (2026-09-05, accepted) — Workflows consume provenance queries; no engine growth

Context: Phase 6 built the provenance surface; Phase 7 asked whether agents *consistently
use* it. The three workflows were upgraded to mandate `pattern-owner`, `attribute`, and
`pipeline-builder` (pass-analysis steps 5b/7b, pipeline-audit provenance chain + swap
outcomes, repo-map provenance maps), then re-executed on AscendNPU-IR.
Decision: keep the engine at the Phase 6 surface — **no new query type was needed**; the
phase's engine changes were small workflow-driven fixes (pattern-owner upward walk,
`k*Attr` idiom capture, CREATES_ATTRIBUTE downgraded to inferred, qualified-id None-guard).
Dossier output now requires: ownership path with per-hop evidence ("Pass uses Pattern X"
alone is invalid), attribute contract or an explicit "graph-confirmed none", and
builder-context justification for pipeline position. Zero-pattern and zero-attribute
claims must be stated as graph-confirmed, not left empty.
Evidence: docs/validation/phase7/ — all six analyses and the regbase audit consumed the
new queries; pattern-map.md (142 chains / 190 confirmed-zero) and attribute-map.md
(86 attrs, 43 with creators) generated from the workflow.
Consequences: query cost per analysis rises to ~6-10 queries (still far below grep);
creator-side attribute semantics remains `inferred` (RG-1) and is the top remaining gap.

## ADR-014 (2026-09-05, accepted) — Ascend ecosystem scope; generic fixes only from second-repo evidence

Context: Phase 8 validated the harness on triton-ascend (Triton→TTGIR/LLVM + Triton→Linalg
Ascend path) with AscendNPU-IR as baseline (nested checkout excluded from the new corpus).
Decision: the harness targets the **Ascend AI compiler ecosystem**, not "generic MLIR".
Repository-specific concepts (TTIR/TTGIR/TritonAscend/RegBase/HFusion/HIVM) stay out of
the core engine; they live in generated per-repo docs. Second-repo validation produced
two generic extractor fixes (bare generated-base inheritance EG-4; factory suffix
matching) and three documented gaps deliberately NOT implemented without ecosystem-wide
need (EG-1 runOnOperation pipeline mislabel, EG-3 Python pipeline composition, EG-5 gtest
coverage) — each has a generic design recorded in docs/validation/phase8/extractor-gaps.md.
Evidence: triton-ascend-summary.md — 0 diagnostics, provenance queries working cross-repo,
3 pass dossiers, 6 architecture docs generated by the unmodified workflow.
Consequences: next-phase extractor work is ranked by ecosystem relevance
(EG-3/EG-1/EG-5 before any Triton-specific modeling).

## ADR-014 supplement (2026-09-05) — Phase 8 refined: Python/C++ hybrid pipeline boundary

Deepened per the refined Phase 8 goal: the authoritative Ascend flow builder is Python
(`third_party/ascend/backend/compiler.py` `make_ttir`/`make_ttgir` stage lists, exposed
via `ADD_PASS_WRAPPER` PyBind bindings). The graph does not model it (EG-1); the audit
documents the full Python builder → C++ wrapper → pass chain manually
(pipeline-audit/make-ttgir.md), including three coexisting lowering frontiers
(HIVM/HFusion, LLVM, Linalg) and four hidden contracts. Schema decision (goal §10):
dialect-transition edges and Python pipeline nodes both deferred — the former lacks a
workflow consumer, the latter needs its extractor design first. Phase 8 numbering:
EG-1 Python pipeline, EG-2 dialect-transition edges, EG-3 registration idioms.

## ADR-015 (2026-09-05, accepted) — Cross-language compiler construction provenance

Context: Phase 8's headline gap — the Ascend flow's authoritative builder is Python
(`backend/compiler.py` stage lists via PyBind bindings), invisible to the C++ graph.
Decision: model the **binding boundary** as a generic entity (`binding:<name>`), matched
by the PyBind def/wrapper idiom with brace-matched lambda bodies (factory found inside);
model Python pipeline-composition functions by **signature** (pass-manager param/usage),
never by name; resolve the full chain PYTHON_COMPOSES → binding → factory →
BINDING_EXPOSES_PASS → pass. Pipeline-kind correctness: runOnOperation/initialize bodies
are pass methods, not pipeline builders. New query `pipeline-composition <pass>` with a
workflow consumer (pipeline-audit cross-language lens; repo-map composition map).
Evidence: docs/validation/phase9/ — 15 chains in triton-ascend
(pipeline-composition-map.md), AscendNPU-IR regression clean (runOnOperation nodes 0,
RegBase builders intact), two dossier "why here" upgrades. Implementation notes: Python
parsing via stdlib ast with BOM stripping (vendor files carry U+FEFF).
Consequences: Python-pipeline provenance is now a generic capability, not a Triton
feature; attribute creator semantics (RG-1) and pm.run verification edges remain open.

## ADR-016 (2026-09-05, accepted) — Semantic boundary graph: dialect transitions + lightweight attribute roles

Context: Phases 6-9 answered construction provenance ("who/where/why here"); Phase 10
targets semantic boundaries ("what abstraction changes here").
Decision:
1. `DIALECT_TRANSITIONS_TO` edges with `role: input|output`, two evidence paths:
   confirmed from the `ConversionTarget` idiom (namespace-qualified dialect names
   supported, attributed to the enclosing pass class) and inferred from pattern op
   ownership propagated through populator chains. Dialect→dialect pairs derived at query
   time, not stored.
2. Attribute semantic roles are lightweight keyword-derived node annotations
   (`heuristic` confidence), deliberately NOT an attribute evaluator; agent reasoning
   completes roles the table cannot express (validated on
   RegisterTreeReductionSelectedAttr).
3. Queries `dialect-transition <pass>`, `semantic-contract <attr>`, `boundary <pass>`,
   each with workflow consumers added in the same phase (pass-analysis step 7a,
   pipeline-audit lens 1a).
Evidence: docs/validation/phase10/ — triton-to-annotation's TritonAscend→Annotation
transition fully evidenced; both repos rebuilt; no regressions.
Consequences: EG-2 closed; the boundary question is answerable per pass; external-dialect
outputs (cross-repo boundaries) remain the known limit (QG-7).

## ADR-016 supplement (2026-09-05) — Refined Phase 10 review answers

1. **Dialect transition belongs in the generic schema** — validated on both repos with
   zero repo-specific naming; confirmed via ConversionTarget idiom, inferred via pattern
   op ownership. No `DialectTransition` entity needed; the edge + query-time pairs are
   sufficient.
2. **Attribute semantic contract does NOT need an independent entity** — the role is a
   heuristic annotation on the attribute node + producer/consumer edges; an entity per
   contract would duplicate the attribute itself. Keyword table bug found and fixed
   during refinement (character-iteration false positives made
   RegisterTreeReductionSelectedAttr claim a wrong role; now honestly `unknown` — agent
   reasoning completes it, as the AV2 dossier demonstrates).
3. **Semantic relations still not deterministic**: attribute *creator vs consumer*
   intent (RG-1), cross-repo output dialects (QG-7), template-pattern matched ops
   (triton-to-linalg canonicalizers), type-conversion-driven transitions (no type
   graph). None blocked the phase's workflows.
4. **Next phase**: continued evidence-based order — EG-1 remainder (Python stage lists
   as first-class pipeline nodes), RG-1, QG-7. Attribute value semantics (A) stays
   deferred: the role layer proved sufficient for the dossiers; runtime contract graph
   (B), clangd (C), MCP (D) unchanged (no blocking evidence).
