# Workflow: Pipeline Audit (`pipeline-audit`)

Agent-independent methodology — the source of truth. Agent skills/prompts wrap this file.

## When to run

Cross-pass review of one pipeline: finding implicit contracts, fragile orderings, and
architecture risks. Not a sequence of per-pass summaries (`pass-analysis.md` does that).

## Input

Pipeline name (e.g. the repo's main compile pipeline) or a pass name to audit its full
pipeline neighborhood.

## Mandatory first move: RepoMap before source

```
mlir-repomap pipeline <name>     # ordered stages, guards, scopes, sub-pipelines, callers
mlir-repomap pipeline-builder <name>   # builder function(s), nested builders, call sites
mlir-repomap tests <pipeline>    # which lit tests exercise it (with feature tags)
mlir-repomap changed [base]      # recent changes touching pipeline files → audit focus
```

Pipeline provenance chain (mandatory): Pipeline → builder function (file:line) → nested
builder calls → pass insertion sites (`addPass` evidence) → pass sequence. Bare-name
pipeline queries may return several file-qualified candidates (same-name builders in
different files are distinct pipelines); audit each candidate separately and say which
target/configuration each belongs to.

Then read only the evidence-pointed regions of pipeline builder files. The pipeline graph
plus guard text replaces repository-wide searching.

## Audit lenses (each produces findings or explicit "checked, OK")

1. **Ordering dependency + justification** — for each consecutive stage pair, what makes
   the order load-bearing, and *why is A before B* — answer with the swap experiment:
   state the concrete failure if the order is exchanged (silent wrong result / compile
   error / no-op degradation). Flag pairs whose contract is only implicit (a flag/enum set
   by an earlier pass, e.g. `decomposePhase = AFTER_<X>` consumed by a later pass) with no
   verifier. Justifications must reference the builder insertion site from the provenance
   chain, not just the extracted order.
1x. **Cross-pass optimization flow** — across the whole pipeline, build the
   opportunity ledger: which stage **creates** an optimization opportunity (e.g.
   normalization/fusion enabling vectorization), which stage **blocks** one (a guard
   whose condition excludes a legal-in-principle case — cite the HAS_CONSTRAINT
   evidence), and where a **tradeoff** is introduced (a stage option or ordering choice
   that buys one optimization at another's expense). The ledger is agent reasoning over
   deterministic facts; every entry cites its constraint/transition evidence.

1y. **Optimization flow lens** — using `pass-intent` / `pass-constraints` across the
   pipeline's stages, report which optimization opportunities are **created** (a stage
   enables a later one) and which are **lost** (a guard blocks a fusion/layout/scheduling
   opportunity — cite the constraint's evidence line). Opportunities are agent-layer
   conclusions over deterministic constraint facts; label them accordingly.

1z. **Ecosystem boundary lens** — when the pipeline's final stages produce IR for
   another compiler repository (visible via
   `mlir-repomap ecosystem handoff --repos <stack repos>`), record the handoff:
   repository pipeline → external compiler stage → next repository, with the consuming
   passes. State which contracts (dialects, ops, attributes) cross the boundary and who
   owns them.

1a. **Dialect-transition lens** — for the pipeline's stages, run
   `mlir-repomap dialect-transition <pass>` (or `boundary`) and assemble the dialect
   evolution: pipeline stage → dialect transitions → hardware boundary. Mark the stage
   where the *abstraction level drops* (high-level tensor/loop IR → hardware-aware IR)
   and every pass whose input dialect is another stage's output dialect — those
   input/output pairs are the pipeline's semantic spine.

1b. **Cross-language provenance lens** — every pipeline must answer: *where does it
   originate?* If stages cannot be explained by C++ builders, run
   `mlir-repomap pipeline-composition <pass>` per stage and reconstruct the chain
   **Python composition function → binding (`m.def`/wrapper) → C++ factory → pass**,
   each hop with file:line. Python stage lists (e.g. `make_*` functions calling
   `passes.<group>.add_*(pm, ...)`) are pipeline builders in the full sense — audit
   their order, guards, and options with the same rigor as C++ builders, and state
   which language constructs the pipeline and where passes are inserted.

2. **Hidden invariants / cross-pass state (attribute contracts)** — pass options or IR
   markers that one stage writes and another reads. For every annotation/metadata/marker
   attribute discovered in the stages, run `mlir-repomap attribute <Name>Attr` and record
   the producer → attribute → consumer chain inside this pipeline; a producer in pipeline A
   consumed in pipeline B is exactly the cross-pipeline contract this lens exists for.
   Classify by how they would fail (wrong result vs compile error).
3. **Conditional duplication** — the same pass (or pipeline phase like bufferize) running at
   two guarded positions. Check the guards are mutually exclusive and both branches keep
   downstream invariants. Mutual exclusion must be verified from guard text, not assumed.
4. **Duplicate analysis** — passes that rebuild the same expensive state (alias maps,
   dominance-based scans) per run; candidates for registered analyses.
5. **Premature lowering / lost abstraction** — stages that drop to a lower dialect before
   the last optimization that needs the higher one (e.g. bufferizing before a
   tensor-level merge).
6. **Missing verification** — stages whose output invariants are unchecked and which have
   no lit test exercising their failure mode.
7. **Architecture leakage** — target/config knowledge leaking into generic stages; macros
   gating stages (`condition_kind: "macro"`) that silently change the pipeline between
   build configurations.
8. **Coverage gap** — end-to-end tests (`test_exercises_pipeline`) vs the guarded variants:
   which guard combinations have no test? RepoMap reports "no discovered test"; conclusions
   about untested-but-supported combinations belong to human reasoning, marked as such.

## Findings format

Same as pass-analysis §Defect classification: Problem / Evidence / Trigger / Impact /
Confidence (Confirmed | Highly Likely | Potential) / Fix direction. Category:
Correctness, Coverage, Performance, Architecture, Maintainability. Never report code
complexity as a defect.

## Output

`docs/compiler-architecture/pipelines/<Pipeline>.md` with sections:
`# Pipeline Overview` (stage flow w/ guards + builder provenance chain) · `# Findings`
(numbered, classified, each ordering finding with a swap outcome) · `# Invariant Map`
(who writes/reads each cross-pass marker, attribute contracts included) · `# Coverage` ·
`# Recommendations`. Register in `pipeline-map.md`.
