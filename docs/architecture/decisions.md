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

## ADR-017 (2026-09-05, accepted) — Ecosystem layer: cross-repository handoff without touching per-repo graphs

Context: Phase 10 left cross-repo boundaries (QG-7) unresolved; the Ascend stack spans
triton-ascend (producer of HIVM/HFusion/Annotation inputs... consumer of their dialects)
and AscendNPU-IR (definer of those dialects/ops).
Decision: keep per-repo indexes authoritative and self-contained; add a generic
**ecosystem layer** that opens N indexes and derives handoff records by artifact-name
matching: (1) dialect handoff = consumer's DIALECT_TRANSITIONS_TO output dialect defined
in another repo (confirmed, ConversionTarget evidence); (2) operation handoff = consumer's
PATTERN_CREATES_OP op defined+owned in another repo (confirmed; op index keyed by both
TableGen class name and mnemonic — the name/mnemonic mismatch was found and fixed during
validation); (3) cross-repo attribute contracts by dual-repo references. Repository
identity is the index path; no repo names in the engine. Exposed as
`mlir-repomap ecosystem --repos … <status|handoff|boundary|contract>`.
Evidence: docs/validation/phase11/ — 2 confirmed dialect handoffs (Annotation, HIVM),
10 op handoffs (MarkOp→Annotation, AtomicRMWOp→HIVM, Conv*/Histogram→HFusion, ...),
5 cross-repo attribute contracts, complete triton-ascend boundary view.
Consequences: QG-7 closed at the ecosystem level; handoff matching is name-based
(versioned artifact identity remains open); runtime-level handoffs out of scope.

## ADR-018 (2026-09-05, accepted) — Intent & constraints: deterministic substrate, agent-owned reasoning

Context: the ecosystem graph answers construction/semantic questions; review workflows
need "why does this pass exist / what blocks this optimization".
Decision: (1) constraints are deterministic per-occurrence graph facts —
`constraint:<file>:<line>` nodes + HAS_CONSTRAINT pass edges for legality-guards,
match-failures, terminal pass-failures and TODO/FIXME notes, extracted from pass classes
AND out-of-line method bodies; (2) intent is a LAYERED VIEW (`pass-intent`): graph facts
only (td stated intent, deterministic label with confidence, boundary evidence,
constraint counts) — agent interpretation must stay in dossier sections explicitly
labeled as reasoning; the engine never records interpretation; (3) optimization
opportunities are dossier-layer records (no query, no node) built on the constraint
substrate.
Evidence: docs/validation/phase12/ — 177 constraints on AscendNPU-IR (171 pass-level),
five dossiers upgraded with separated fact/interpretation sections.
Consequences: the graph cannot "lie" about design intent; reasoning provenance is
visible by which layer a claim comes from. Multi-line condition truncation and
helper-scoped guards are recorded limitations.

## ADR-019 (2026-09-05, accepted) — Review intelligence: three-layer separation, doc-layer review records

Context: with the constraint substrate (ADR-018) in place, review workflows can produce
design-level findings; the risk is polluting facts with judgment.
Decision: (1) review records are **doc-layer artifacts** in the target repo's dossiers
with a fixed format (Intent / Protected Invariants — each tied to its enforcing
constraint or marked UNGUARDED / Constraints / Tradeoffs / Risks / Opportunities with
the five-part opportunity format); (2) the workflow mandates reporting **unguarded
invariants** — contracts with no enforcing HAS_CONSTRAINT edge — as the highest-value
findings; (3) no engine changes, no review persistence until cross-session review
querying becomes a real need; (4) pipeline-audit gains the cross-pass optimization-flow
ledger (creates/blocks/tradeoff).
Evidence: docs/validation/phase13/ — five review records; signature findings are all
unguarded-invariant discoveries (merge-vf single-use assumption, AV2 verifier
completeness, triton-to-annotation name validation, triton-to-linalg cross-dialect
flatten contract).
Consequences: reasoning provenance is visible by layer; the graph remains a facts-only
contract; RG-1 stays backlog (ownership resolvable by reasoning).

## ADR-020 (2026-09-05, accepted) — Compiler findings: doc-layer lifecycle artifacts + deterministic git drift tracking

Context: Phase 13 review records are one-shot dossier sections; compiler findings
(unguarded invariants, opportunities, historical concerns) had no durable lifecycle and
no mechanism to notice when their evidence changed under them.
Decision: (1) findings are **doc-layer YAML artifacts** (`<ID>.yaml`, one per file) in the
target repo's `docs/compiler-architecture/findings/` — never graph entities; the graph
stays facts-only. (2) The engine provides only deterministic services over them:
strict-subset parsing with fail-soft diagnostics, schema/lifecycle validation
(every status transition requires reason + evidence/reference; superseded requires
superseded_by), and git-aware drift detection (commits touching evidence files since
`review.baseline_commit`, snippet-presence verification reporting "evidence changed").
(3) The engine **never mutates status and never judges a fix** — `findings check`
outputs "possibly affected by commit X / Needs review" in the goal format; lifecycle
advancement is an agent/human edit with recorded reasoning. (4) Workflows consume it:
pass-analysis step 0 (evolution check) and pipeline-audit lens 1e (risk delta).
Evidence: docs/validation/phase14/ — 7 seeded findings across both repos (5 AscendNPU-IR,
2 triton-ascend, one with dual-repo evidence), real-history drills flagging the exact
commits recorded in regression memory (fa682a1a3, 7875b76ea), a clean true-negative
(TTA-001), 25/25 tests.
Alternatives: findings as graph nodes (rejected: agent reasoning disguised as facts);
automatic status resolution from git (rejected: violates the three-layer separation and
the "no auto fix judgment" rule); full YAML library (rejected: stdlib-only portability).
Consequences: no INDEXER_VERSION bump (index untouched); a new FindingService joins the
contract surface; line-granular commit attribution and a baseline convention for
pre-mechanism findings are recorded gaps.

## ADR-021 (2026-09-05, accepted) — Attribute creator provenance: container-typed creators, mechanism-classified lines

Context: RG-1 — attribute provenance could say where an attribute is *referenced* and
(weakly) which pass class mentions it, but not who creates it, where it is attached, or
which verifier assumes its semantics. Phase 14 findings TTL-001/TTA-001 cited this gap
directly.
Decision: (1) creator typing is **container classification** over brace-matched spans —
pattern class with conversion base → ConversionPattern, other rewrite bases →
RewritePattern, op `build` method → OpBuilder, pass class/method → Pass, OpPassManager
function building a pipeline → PipelineBuilder, free function taking
PatternRewriter&/ConversionPatternRewriter& → pattern-side helper (signature rule, same
principle as the RewritePatternSet& populator rule, ADR-012). (2) **Mechanism is read
from the reference line**: `XxxAttr::get(` = construction, `setAttr/addAttr/addAttribute`
= attachment (`attach: true`), `getAttr/removeAttr/hasAttr` or plain mention = read →
consumer (`role: verifier` for verify methods, else reader). A mention alone never
creates a creator edge. (3) Verifier is recorded as a *consumer* semantics-dependency,
not a creator — recording verifiers as creators would be a false fact (goal listed
Verifier among creator types; only source-provable roles are kept). (4) td definition
join (`attr:<Name>` + DIALECT_OWNS) happens at query time in the new
`attribute-provenance` query; definition-only attributes are served from the td side
with a diagnostic. (5) The old containment-based CREATES_ATTRIBUTE extraction in
cpppass.py is removed — replaced by typed edges; this deliberately *shrinks* creator
lists (v43's lists contained false creators such as reads via hasAttr).
Alternatives rejected: verifier-as-creator (false facts); Python `Pass(..., attr=)`
kwarg detection (no occurrence in the validation repos — not implemented, recorded);
per-attribute attribution of dynamic `setAttrs(op->getAttrs())` forwarding
(name-agnostic, not attributable — TTA-001 limitation, kept honest).
Evidence: docs/validation/phase15/ — real chains: StrideAlignDimsAttr creator
pattern:NormalizeAlignInfoPattern (attach, EnableStrideAlign.cpp:98) with consumers
including the conversion boundary; TreeReductionSelectionFrozenAttr creator pass:vf-fusion
(attach, VFFusionPass.cpp:168) — the VFFusion↔AutoVectorizeV2 contract; MultiBufferAttr
creator reduced 3 (v43, 2 false) → 1 true (pattern-helper mark(), MarkMultiBuffer.cpp:238);
ecosystem contract creators for SyncBlockLockUnorderedAttr / TCoreTypeAttr now typed.
Consequences: INDEXER_VERSION 45 (full re-index); CREATES_ATTRIBUTE gains creator_type /
attach props and pattern/function/symbol sources; ecosystem creator lists become
mechanism-honest; no new node kinds, no findings/reasoning in the graph (ADR-019/020
separation intact).

## ADR-022 (2026-09-05, accepted) — Semantic finding impact analysis: structural signals only, scope suggestion never a verdict

Context: Phase 14's drift check is file-level ("commit touched an evidence file");
it cannot say which compiler entity changed, which guard set changed, or which tests
guard the affected area. Findings need a bridge from the doc layer back into the graph.
Decision: (1) findings may declare optional `entity_refs` — single-key `kind: id`
references to EXISTING graph entities; resolution happens at query time (exact id →
unique name → explicit ambiguity/not-found uncertainty); findings never create nodes.
(2) `finding-impact <id>` joins resolved entities + per-evidence-file git drift +
constraint evolution + TEST_COVERS_PASS edges into one deterministic report ending in
a review-scope *suggestion* (affected passes with their constraint-area counts and
linked tests). (3) Constraint evolution diff (`constraint-diff <file> --since`) reuses
the Phase 12 scanner extracted verbatim as `cpppass.scan_constraints` (output-preserving:
constraint counts identical on both repos after full re-index) and classifies
structurally only — "possible weakening (guard(s) removed)" / "possible strengthening" /
"changed guard set" / "guards moved" — never a semantic judgment of correctness.
(4) Test coverage signal (EG-5 stage 1): lit RUN-flag links upgrade to `exact` when the
flag is a confirmed pass arg; gtest files (TEST/TEST_F idiom) become test nodes linked
by normalized test-name containment with `heuristic` confidence. Rejected:
**cross-repository ecosystem validation** (resolving entity_refs across repo indexes
and validating handoff contracts) — complexity above benefit for now; cross-repo refs
resolve against the opened index only and unresolvable refs surface as explicit
uncertainty (validated with TTL-001). Also rejected: auto-status mutation from impact
signals (ADR-020 stands); semantic weakening/strengthening interpretation.
Limitations: constraint diff is per-file text-level (guards matched by kind+normalized
text, so reformatting a condition counts as removed+added); gtest linking is name-level;
lit `exact` means flag==pass-arg, not "this test truly exercises this pass path".
Evidence: docs/validation/phase16/ — AV2-001 impact against the pre-fallback baseline
(commits [fa682a1a3], guard `failed(result` added at :1406 → "possible strengthening"),
MVS-001 against pre-migration (4 commits incl. 4ddead06f, "file absent at base"),
TTL-001 single-repo (attribute exact / cross-repo pass uncertainty); tests 38/38.
Consequences: INDEXER_VERSION 46 (gtest nodes + evidence confidence upgrade); the
confidence ladder gains `exact` (heuristic < inferred < exact < confirmed); per-file
diagnostics are cleared on successful re-extraction (stale diagnostics hygiene).

## ADR-023 (2026-09-05, accepted) — Compiler review memory: verbatim records, structural retrieval, no generated reasoning

Context: review knowledge (Phase 13 records, Phase 14 findings, constraints, Phase 16
impact) existed but was spread across four surfaces; an agent had to re-assemble it
before every analysis (docs/validation/phase17/review-memory-gap.md).
Decision: (1) `review <pass>` joins — in one deterministic query — the graph pass
identity, the dossier's Compiler Review record extracted VERBATIM from
`docs/compiler-architecture/passes/*.md` (located by filename stem or content mention
of the pass arg; multiple matches are all returned), findings linked by pass-field or
entity_refs, the pass's HAS_CONSTRAINT records as the deterministic invariant guards,
and per-finding recent impact signals (Phase 16, own baseline or --since). Records are
quoted, never regenerated; empty memory is an explicit note. (2) The `evidence`
command becomes an evidence catalog: entity + evidence rows + findings referencing the
entity (structural matches only: evidence.ref, evidence.file, entity_refs) + recent
commits touching the entity's file. (3) Data ownership unchanged: the graph owns
facts, the dossier/findings docs own review reasoning, the engine only retrieves and
joins; lifecycle stays human-controlled (ADR-019/020).
Rejected: **embedding memory / semantic similarity** (retrieval must stay
structurally explainable — matches are name/ref equality); **automatic review**
(the engine never writes review records or updates them from code changes — a new
review is an agent workflow run); **cross-repo validation** (carried from ADR-022:
review resolves against one index; cross-repo artifacts surface as notes/uncertainty).
Limitations: dossier location relies on the documented docs layout convention; record
extraction is header-based ("# … Compiler Review …" to the next top-level header);
evidence-file matching can over-match when several entities share one file (matched_via
is always shown so the agent can judge).
Evidence: docs/validation/phase17/ — review AutoVectorizeV2 returns the verifier
invariant + fallback history (fa682a1a3) + guard evolution in one call; review
MergeVecScope returns the unguarded single-use assumption (record) + verify guards
(:1422/:1625); evidence catalog links AV2-001 to constraint:…:1406 via evidence.ref
with fa682a1a3 as recent history; tests 42/42.
Consequences: no schema change, no INDEXER_VERSION bump; query-api gains `review` and
the extended `evidence` catalog; workflows consume them (pass-analysis step 0, lens 1g).
