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
