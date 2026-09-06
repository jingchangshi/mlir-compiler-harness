# Finding Impact Gap — from "file changed" to "what to review"

Phase 16 design document (Step 1). Status quo reproduced from the Phase 14 machinery
(`findings check`, commit 206416b) against the real findings.

## What the current loop can answer

Phase 14 gave findings git-aware drift: `findings check` reports, per finding,
**commits touching evidence files** since the baseline and **snippet verification**
("evidence changed"). That is a *file-level* signal:

```
Finding AV2-001
possibly affected by commit fa682a1a3 ([HFusion] enable MCF by default and drop
AutoVectorizeV2 retry/fallback) (+19 more)
Needs review
```

## What it cannot answer (the gap, with the real findings)

| question | AV2-001 | MVS-001 | TTL-001 |
|---|---|---|---|
| **Which compiler entity changed?** | the commit list names files, not entities — nothing links `fa682a1a3` to `pass:hfusion-auto-vectorize-v2` | same for MergeVecScope.cpp → `pass:hfusion-merge-vf` | TritonToLinalgPass.cpp drift says nothing about `pass:triton-to-linalg` |
| **Which invariant/constraint is affected?** | the finding's guard (`constraint:…AutoVectorizeV2.cpp:1406`) may have moved, changed condition, or disappeared — invisible | the unguarded single-use assumption (MergeVecScope.cpp:631) has no constraint to diff at all — only file drift | producer-side references are unattributed; no per-file constraint view |
| **Which constraint changed (added/removed/moved)?** | no comparison exists between the constraint set at the finding's baseline and now (the v43→v45 retry/fallback removal actually changed the guard set — undetectable) | same | same |
| **Which tests are related?** | not surfaced at all — `TEST_COVERS_PASS` exists in the graph but the finding loop never consults it; gtest coverage is not extracted (EG-5) | same | same |
| **Review scope?** | "Needs review" with no area | same | same |

Root cause: a finding's evidence is `file:line` text only. The graph knows about
entities, constraints, and tests — but the finding loop never joins them.

## Design consequence (Steps 2–5 of the phase)

1. **Entity-aware references** (Step 2): findings may declare `entity_refs` —
   references to *existing* graph entities (pass/pattern/attribute/operation/…).
   Findings still create no nodes; unresolvable refs become explicit uncertainty.
2. **Finding impact** (Step 3): `finding-impact <id>` joins resolved entities + file
   drift + constraint diffs + test coverage into one deterministic, evidence-backed
   report with a *scope suggestion* (never a verdict).
3. **Constraint evolution diff** (Step 4): compare the deterministic constraint set of
   a file between a base commit and now (added / removed / moved / changed), with
   structural classification only ("possible weakening = a guard disappeared") — no
   semantic interpretation of whether the change is correct.
4. **Test coverage signal** (Step 5): surface `TEST_COVERS_PASS` for affected passes;
   lit flag links carry `exact` confidence when the flag is a confirmed pass arg;
   gtest files are extracted and linked by test-name heuristic only (`heuristic`).
   No coverage is invented.
