# Workflow: MLIR Pass Deep Analysis (`pass-analysis`)

Agent-independent methodology — the source of truth. Agent skills/prompts wrap this file.

## When to run

Deep analysis of one (or few) concrete pass(es): understanding, design review, defect hunt,
or producing a durable dossier in the target repo.

Scope guard: single-pass depth. Cross-pass contracts belong to `pipeline-audit.md`.

## Input

A pass name in any of these forms: pass argument (`hfusion-merge-vf`), td class
(`MergeVecScope`), factory (`createMergeVecScopePass`), or C++ class. Resolution order:
exact pass arg → unique substring match → td class / factory via `repo symbol`.

## Mandatory first move: RepoMap before source

```
mlir-repomap pass <name>
```

gives: definition (td + cpp), factory, registration, pipeline memberships with guards and
predecessor/successor, patterns (matched/created ops), tests, evidence pointers. Then read
**only** the files those pointers name. Repository-wide grep is prohibited unless a dossier
section cannot be filled from queries plus pointed files — and if that happens, record which
query would have answered it (feeds the query-API review).

## Fixed analysis spine (all 13 steps, in order)

1. **Pass identity** — arg, td class, summary, cpp class; note which identity came from
   evidence vs heuristic.
2. **Registration** — `let constructor` factory, any PassRegistration, option definitions.
3. **Pipeline position** — every membership: pipeline, scope (`module` / `nest<Op>`), order
   and cross-scope `seq`, guard. Derive predecessor/successor per membership and what the
   guard means semantically. For each membership pipeline, run
   `mlir-repomap pipeline-builder <pipeline>` and record: builder function (file:line),
   call sites, nested builders, and the insertion site of this pass in the builder body —
   "why this pass sits here" must reference the builder source, not just the order number.
4. **Input invariant** — what IR shape the pass assumes (op set, attribute presence, analysis
   validity, canonical forms). Evidence: pred passes + code guards + test inputs.
5. **Analysis dependencies** — `getAnalysis<>`, ` depend on computed state` (e.g.
   decomposePhase enum set by earlier passes — flag cross-pass state as an audit risk).

5b. **Attribute contract** — if the pass creates, consumes, or is gated by IR attributes
   (annotations, metadata, markers): for each attribute run
   `mlir-repomap attribute <Name>Attr`. Output the full contract: Producer (confirmed
   creator) → attribute → Consumers (referencing files/passes) → attachment relation →
   evidence. If the producer/consumer pair crosses pipelines, state it as a pipeline
   contract in the dossier. A pass with no attribute hits must record
   "no attribute contract (graph-confirmed)" rather than leaving the section empty.
6. **Core transformation algorithm** — the actual algorithm at the level a reviewer needs:
   data structures, iteration order, cost heuristics. Cite `file:line` for each claim.
7. **Output invariant** — what the pass guarantees afterwards; what downstream passes
   rely on (successor passes + their input handling).

7a. **Semantic boundary analysis** — run `mlir-repomap boundary <pass>` and answer:
    *what abstraction changes here?* and **why does this pass exist at this layer?**
    (the layer justification combines the boundary with the pipeline-builder context of
    step 3: the pass exists at this layer because the stage list placed it there, and
    the boundary says what that placement achieves) — input dialects, output dialects, created ops,
    downstream assumptions, and the dialect→dialect transition pairs. A pass with
    transitions is a lowering boundary and the dossier must say so explicitly
    ("this pass is a lowering boundary because: input dialect …, output dialect …,
    created ops …, downstream assumptions …"); a pass with none is an
    optimization/analysis pass at its position — also state that.

7d. **Intent analysis** — run `mlir-repomap pass-intent <pass>`; the query returns
    graph-derived intent facts (stated intent from td, deterministic label with
    confidence, boundary evidence, constraint counts). The dossier must separate:
    graph fact (query output) vs **agent interpretation** ("why does this pass
    exist?" — your reasoning, explicitly labeled as such). Never write an
    interpretation into the graph or present a heuristic label as confirmed.

7f. **Compiler review record** — conclude the dossier with a review section answering,
    in this order: (1) *why does this pass exist?* (intent, layered per 7d);
    (2) *what invariant does it protect?* (each invariant tied to the constraint that
    enforces it — from 7e — or marked "unguarded"); (3) *what optimization opportunity
    may be lost?* (Current behavior / Evidence / Protected invariant / Lost opportunity /
    Possible direction); (4) *what extension direction exists?* The review is an
    agent-layer artifact: every judgment cites graph facts + evidence, and interpretations
    are labeled as reasoning. Unguarded invariants (a contract with no enforcing
    constraint) are the highest-value review findings — report them as such.

7e. **Constraint analysis** — run `mlir-repomap pass-constraints <pass>`; each
    legality-guard / match-failure / early-return / pass-failure record is a
    deterministic fact (condition text + evidence line). Use them to answer *"what
    prevents this optimization from applying?"* and record **optimization
    opportunities** in the dossier (Current / Evidence / Impact / Possible direction)
    — opportunities are agent-layer records, never engine facts.

7c. **Cross-repository contract** — if the pass outputs an artifact consumed by another
    repository in the ecosystem (dialect, op, attribute — visible via
    `mlir-repomap ecosystem handoff <name>` with `--repos` covering the stack), the
    dossier must name: producer, consumer, handoff contract, and the transforming pass.
    Only relevant when an ecosystem index is available; otherwise skip explicitly.

7b. **Pattern provenance** — if the pass registers rewrite patterns (direct or via
   populator chains): for each pattern run `mlir-repomap pattern-owner <Pattern>` and
   document the **ownership path**: Pass → populator function (file:line, call site) →
   intermediate helpers → `patterns.add` site → pattern class → matched/created ops.
   Every hop carries evidence and confidence (confirmed = call-site + definition on the
   chain; inferred = resolved by naming convention or locality heuristic with the
   `disambiguation` flag visible). "Pass uses Pattern X" is never an acceptable
   statement by itself — the dossier must answer *why X belongs to this pass*. A pass
   with zero patterns must state "registers no rewrite patterns (graph-confirmed)"
   instead of an empty list.
8. **Downstream dependency** — successor passes, pipelines, later stages keyed on flags
   set by this pass (search the dossier's pipeline neighborhood for the flag/enum).
9. **Supported scenarios** — IR topologies the pass handles; ground each in a test or code path.
10. **Unsupported scenarios** — topologies it rejects/breaks on. RepoMap can only report
    "no discovered test"; concluding "does not support X" requires code reading. Never present
    absence-of-test alone as proof of non-support.
11. **Test coverage** — from the dossier's tests; note confidence (`heuristic` flag links).
12. **Minimal IR counterexamples** — for suspected defects, construct minimal MLIR showing
    before → pass decision → rewrite → outcome → impact. Run against `bishengir-opt`/tests
    when a build is available; otherwise mark unverified.
13. **Design limitation vs bug** — classify each finding; do not equate "complex code" with
    "bug".

## Defect classification & evidence level

Categories: `Correctness`, `Coverage`, `Performance`, `Architecture`, `Maintainability`.
Each finding carries: Problem / Evidence (file:line + quote or IR) / Trigger condition /
Impact / Confidence / Fix direction.

Confidence ladder:
- **Confirmed** — demonstrated by code logic + reproduced IR or test.
- **Highly Likely** — code path proves the behavior; not yet reproduced.
- **Potential** — reasoning suggests risk; no direct proof.

## Output

`docs/compiler-architecture/passes/<PassArg>.md` with sections:

```
# Overview
# Pipeline Context
# Input / Output Contract
# Algorithm
# Core Data Structures
# IR Examples
# Supported Cases
# Unsupported Cases
# Test Coverage
# Potential Issues
# Recommendations
```

Header provenance block: repo HEAD, RepoMap index version, analysis date, primary files
(+ `file:line` for each load-bearing claim). Register the dossier in `pass-catalog.md`.

## Budget discipline

A pass analysis should need: 1 `repo pass` query + 1–3 `pipeline`/`tests` queries +
1 `pipeline-builder` per membership pipeline + 1 `pattern-owner` per registered pattern +
1 `attribute` per attribute contract + reading ≤5 files pointed to by evidence. If you
exceed this, the gap is an engine finding — record it.
