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
3. **Pipeline position** — every membership: pipeline, scope (`module` / `nest<Op>`), order,
   guard. Derive predecessor/successor per membership and what the guard means semantically.
4. **Input invariant** — what IR shape the pass assumes (op set, attribute presence, analysis
   validity, canonical forms). Evidence: pred passes + code guards + test inputs.
5. **Analysis dependencies** — `getAnalysis<>`, ` depend on computed state` (e.g.
   decomposePhase enum set by earlier passes — flag cross-pass state as an audit risk).
6. **Core transformation algorithm** — the actual algorithm at the level a reviewer needs:
   data structures, iteration order, cost heuristics. Cite `file:line` for each claim.
7. **Output invariant** — what the pass guarantees afterwards; what downstream passes
   rely on (successor passes + their input handling).
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

A pass analysis should need: 1 `repo pass` query + 1–3 `pipeline`/`tests` queries + reading
≤5 files pointed to by evidence. If you exceed this, the gap is an engine finding — record it.
