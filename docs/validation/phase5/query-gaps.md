# Phase 5 Query Gaps (RepoMap Engine)

Collected during the six pass analyses and the regbase audit. No engine changes were made
per Phase 5 rules; each gap has a proposed fix and priority.

## QG-1 — Same-name pipeline builders are merged into one node

- Missing capability: pipeline identity is the function name (`alignStoragePipeline` exists
  in both `HIVMPipelines.cpp` and `HIVMRegbasePipelines.cpp`); the graph merges their
  stages, producing one pass with two different orders (mark-stride-align order 1 and 2)
  and order collisions (fold-alloc-reshape 2 and 3).
- Impact: pipeline stage lists are wrong-by-merge for any repo with same-name builders in
  different namespaces; audit ordering claims degrade.
- Priority: **High** (observed on first audit of a real pipeline).
- Fix direction: qualify pipeline id with defining file/namespace
  (`pipeline:<file>:<name>`), keep name as an alias for unique matches.

## QG-2 — User-facing pass names that match neither arg nor td class

- Missing capability: "HFusionFlattenOps" (the goal's name) resolves to nothing because the
  td class is `FlattenOps` and the arg is `hfusion-flatten-ops`; dialect-prefixed class
  naming is a convention, not code reality.
- Impact: agents following the goal text must fall back to extra queries (we did: arg
  lookup). Not hard-blocking.
- Priority: Low.
- Fix direction: alias candidate set from `get_pass` documentation; optionally accept
  `<Dialect><ClassName>` by splitting on the dialect table.

## QG-3 — PASS→PATTERN ownership missing for free-function `populate*` registration

- Missing capability: all six analyzed passes register patterns via free functions
  (`populateFlattenOpsPattern`, `populatePreVectorizationFusionPatterns`,
  `populateFusionPatterns`, …) with `patterns.add<T>`; the out-of-line
  `runOnOperation` container support (ADR-009) does not cover free functions, so every
  dossier shows `patterns: []`.
- Impact: cannot explain from the graph which rewrite patterns a pass runs — the single
  most recurring friction in this phase (6/6 analyses).
- Priority: **High**.
- Fix direction: chase `populate*Patterns(RewritePatternSet&)` definitions and their call
  sites (Phase 3.5 design); attribute contained `patterns.add` to the enclosing function
  and its callers.

## QG-4 — No attribute-level producer/consumer query

- Missing capability: to answer "who consumes the stride-align marks", a repository grep
  for `StrideAlignDimsAttr` was needed; the graph has no edge kind for IR attribute usage.
- Impact: metadata-contract passes (mark/enable, storage_aligned, decomposePhase) require
  manual searches for their consumer side.
- Priority: Medium.
- Fix direction: extract `Attr.name` references (regex is enough for `*Attr::name`)
  as `attr:<Name>` entities with REFERENCES edges; expose `repo attr <name>`.

## QG-5 — Test links lack feature metadata and pipeline coverage

- Missing capability: `tests <pipeline>` is usually empty (RUN lines name tool flags, not
  builders); no feature dimensions (multi-user / reduction / dynamic-shape / nested-region)
  are attached to tests, so coverage answers like goal §5.1's checklist cannot come from
  the graph.
- Impact: coverage sections of dossiers require opening many test files.
- Priority: Medium.
- Fix direction: derive coarse feature tags from test file names + CHECK bodies
  (heuristic confidence), and link tests to pipelines through the tool-driver flags they
  use (e.g. `bishengir-compile` → entry pipelines).

## QG-6 — Cross-scope execution order is not derivable

- Missing capability: `pipeline <name>` orders stages per scope (`module` counter vs
  `nest<Op>` counter), but the relative execution order of module-scope vs func-scope
  stages (e.g. vf-fusion order 1 module before hfusion-flatten order 3 func) is not
  exposed; the audit had to reason from source.
- Impact: ordering-dependency analysis needs an extra mental join.
- Priority: Medium.
- Fix direction: emit a per-pipeline monotonically increasing `seq` property alongside
  `order`, computed from source position of the addPass statements.
