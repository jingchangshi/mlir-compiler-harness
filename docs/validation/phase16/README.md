# Phase 16 Validation — Semantic Finding Impact Analysis

Date: 2026-09-05 · harness @ Phase 15 (`206416b`) · indexer v46 (full re-index both
repos) · tests 38/38 (32 preserved + 6 new).

Question of the phase: **can the loop say what to review — which entity changed,
which guard set changed, which tests guard the area — without ever judging whether a
fix landed?**

Design basis: `finding-impact-gap.md`. Architecture change: ADR-022. The three-layer
separation (ADR-019/020) is untouched: findings stay doc artifacts, the graph stays
facts-only, and impact reports are deterministic signals ending in a *suggestion*.

## 1. Architecture change summary

- `findings.py`: optional `entity_refs` (single-key `kind: id` mappings, kinds
  pass/pattern/attribute/op/pipeline/function/dialect) validated at load; resolution
  against the graph at query time — findings never create nodes; unresolvable refs
  become explicit uncertainty.
- `impact.py` (new): `ImpactService.impact(id)` — resolved entities + per-file git
  drift + constraint evolution + test coverage → review-scope suggestion;
  `constraint_diff(file, since)` — structural guard-set diff.
- `cpppass.py`: the Phase 12 constraint scanner extracted verbatim as
  `scan_constraints()` so diffing runs the identical logic on historical text.
  Output-preserving: constraint node counts identical after full re-index
  (AscendNPU-IR 390, triton-ascend 53).
- `tests.py` + `index.py`: gtest files (TEST/TEST_F) become test nodes (EG-5 stage 1);
  lit RUN-flag links upgrade to `exact` when the flag is a confirmed pass arg;
  gtest links by normalized test-name containment (`heuristic`). Confidence ladder:
  heuristic < inferred < exact < confirmed. Per-file diagnostics are cleared on
  successful re-extraction (stale-diagnostics hygiene fix).

## 2. New query capability

```
mlir-repomap finding-impact <finding-id> [--dir D] [--git-repo R] [--since REF]
mlir-repomap constraint-diff <file> --since REF
```

Report shape: `finding` → `affected_entities` (with resolution confidence) →
`changed_signals` (`file-commits`, `constraint-diff` with structural classification)
→ `test_signal` (exact/heuristic) → `review_scope` (areas + suggestion) →
`uncertainty`/`diagnostics`/negative-result `note`. No signal is ever fabricated:
without evidence the report says so.

## 3. Finding impact examples (Step 7, real history)

**AV2-001** (`--since` = parent of `fa682a1a3`, the fallback-removal commit):

```
ENTITIES: pass:hfusion-auto-vectorize-v2 (exact)
COMMITS:  AutoVectorizeV2.cpp ← fa682a1a3   [fallback removed]
DIFF:     possible strengthening (guard(s) added)
          added: legality-guard @1406 "failed(result"
SCOPE:    Review pass:hfusion-auto-vectorize-v2 (constraints: legality-guard 1);
          39 linked tests to re-run/inspect
```

The report turns the Phase 14 "possibly affected by fa682a1a3" into a structural fact:
the acceptance guard did not exist before the fallback was removed — the guard set
*grew* when the retry path disappeared (matching the finding's regression memory).

**MVS-001** (`--since` = parent of `4ddead06f`, the A5 migration):

```
ENTITIES: pass:hfusion-merge-vf (exact)
COMMITS:  4 — including 4ddead06f itself
DIFF:     no baseline content (file absent at base ref)   ← the pass was born here
SCOPE:    Review pass:hfusion-merge-vf (constraints: legality-guard 2 — the two
          mergedFunc.verify guards); 4 linked tests
```

The unguarded single-use assumption has no constraint to diff — exactly the finding's
point; the report's constraint area shows only the two verify guards that DO exist.

**TTL-001** (single-repo validation, per goal §7):

```
ENTITIES: attribute:StrideAlignDimsAttr (exact) · pass:triton-to-linalg → not-found
UNC:      "no pass entity found for reference 'triton-to-linalg' (uncertainty,
          not a fact)" + external-repo evidence note
SCOPE:    Review attribute:StrideAlignDimsAttr (no drift since baseline)
```

The cross-repo pass ref resolves only against the triton-ascend index; the opened
index is AscendNPU-IR — the rejection of cross-repo ecosystem validation (ADR-022)
made visible as honest uncertainty, not a wrong fact. With `--since 2bafba14a` the
triton-side drift fires: 2 commits on TritonToLinalgPass.cpp.

## 4. Constraint evolution examples

```
$ mlir-repomap constraint-diff bishengir/lib/Dialect/HFusion/Transforms/AutoVectorizeV2.cpp --since <pre-fa682a1a3>
classification: possible strengthening (guard(s) added)
added:  legality-guard @1406 "failed(result"
```

Structural labels only — "possible weakening (guard(s) removed)" / "possible
strengthening (guard(s) added)" / "changed guard set" / "guards moved" — the engine
never says whether a weakening is a bug (goal §4: no semantic interpretation).

## 5. Test coverage signal

- lit: RUN-line flag → pass arg identity, `exact` when the pass node exists
  (934 exact links on AscendNPU-IR, 242 on triton-ascend).
- gtest: 4 test nodes on AscendNPU-IR (FilterPassesTest.cpp among them), 3 on
  triton-ascend; links by name containment only (1 and 7 heuristic edges).
- Both surface inside `finding-impact` as the re-run list of the review scope.

## 6. Tests

38/38. New `FindingImpactTest` (6): entity-ref validation (bad kind rejected);
impact query with real signals (file-commits + constraint-diff "changed guard set"
with `dim > 4`→`dim > 8` on a controlled git repo, entity resolved against the
fixture graph); negative case (baseline = HEAD → zero signals, explicit negative
note); unresolved ref → uncertainty, never an impact claim; constraint-diff
classifications (strengthening / weakening); gtest coverage signal (linked
`SimpleFold*` test, unrelated suite NOT linked, lit links exact).

## 7. ADR/status changes

ADR-022 (problem/design/rejected/limitations — cross-repo ecosystem validation
explicitly rejected: complexity above benefit for now); status.md Phase 16 section;
roadmap next = review-scope watchlist delivery + EG-1 remainder; query-api.md gains
the two commands.

## 8. Remaining limitations

- Constraint diff matches guards by (kind, normalized text) per file: reformatting a
  condition reads as removed+added ("changed guard set"); line-precise tracking needs
  a semantic backend (still deferred).
- gtest linking is name-level ("heuristic"); no gtest body analysis.
- lit `exact` = flag-is-pass-arg, not proof the test exercises the pass's code path.
- entity_refs resolve against ONE index; cross-repo refs are uncertainties (rejected
  cross-repo validation, ADR-022).
- Impact reports never mutate finding lifecycle (ADR-020) — by design, no automation
  of status was built.

## 9. Why this improves the Compiler Knowledge Evolution Loop

The loop now closes its last reasoning gap *deterministically*:

```
changed compiler entity   (entity_refs → graph resolution)
      v
affected invariant        (constraint-diff: guard set evolution, structural)
      v
affected finding          (file drift + evidence refs joined per finding)
      v
review scope suggestion   (constraint areas + exact/heuristic test lists)
```

Phase 14 said *that* something changed; Phase 16 says *what to review about it* —
which pass areas, which guards grew or shrank, which tests to re-run — while leaving
every judgment (is it a bug? is the finding resolved?) to the human/agent owners.
Findings become review-guided instead of review-triggering, and each element of the
suggestion carries its own file:line evidence.
