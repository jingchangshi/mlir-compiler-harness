# Phase 17 Validation — Compiler Review Memory & Evidence Retrieval

Date: 2026-09-05 · harness @ Phase 16 (`47e5ccf`) · indexer v46 (unchanged — no
schema/extractor change) · tests 42/42 (38 preserved + 4 new).

Question of the phase: **can an agent load everything the loop already knows about a
pass — review record, invariants, findings, evidence, recent drift — in one
deterministic query, without generating any reasoning?**

Design basis: `review-memory-gap.md`. Architecture change: ADR-023. The three layers
are untouched: the engine retrieves and joins; the dossier/findings docs own the
reasoning; lifecycle stays human-controlled.

## 1. Architecture change summary

- `ImpactService.review(pass, since)` (new): one query returning — pass identity
  (multi-strategy resolution: arg/td class/cpp class/factory), **Compiler Review
  records** extracted verbatim from `docs/compiler-architecture/passes/*.md`
  (located by filename stem or content mention; all matches returned with
  dossier:line), **findings** linked by pass-field or `entity_refs`, **invariant
  guards** (the pass's deterministic HAS_CONSTRAINT records), and **recent impact
  signals** per finding (Phase 16 machinery, own baseline or `--since`).
- `evidence <entity>` extended into the **evidence catalog**: entity + evidence rows
  + `referenced_by_findings` (structural matches: `evidence.ref`, `evidence.file`,
  `entity_refs` — always shown as `matched_via`) + `recent_history` (commits
  touching the entity's file). No embedding, no semantic similarity — anywhere.

## 2. New query capabilities

```
mlir-repomap review <pass> [--dir D] [--docs-dir D] [--git-repo R] [--since REF]
mlir-repomap evidence <entity-id>          # now a full evidence catalog
```

## 3. Review memory examples (Step 5, real data)

**AV2-001 / AutoVectorizeV2** — one call (`review hfusion-auto-vectorize-v2 --since
<fa682a1a3^>`) returns the goal's three required elements:

```
RECORDS: auto-vectorize-v2.md:187 (verifier-completeness invariant — 'verifier'
         present in record), vf-fusion.md:165 (content mention — all matches shown)
FINDINGS: AV2-001 (entity_refs, has regression memory: fallback crash fix
          7875b76ea + fallback removal fa682a1a3), VFF-002
GUARDS:  legality-guard @1406 (the acceptance guard)
IMPACT:  fa682a1a3 + constraint-diff "possible strengthening (guard(s) added)"
```

**MVS-001 / MergeVecScope** — `review hfusion-merge-vf --since <4ddead06f^>`:

```
RECORDS: merge-vec-scope.md:197  (records the UNGUARDED single-use assumption)
FINDINGS: MVS-001, MVS-002 (entity_refs)
GUARDS:  legality-guard @1422, legality-guard @1625  (the two verify guards)
IMPACT:  4 commits incl. 4ddead06f; constraint-diff "no baseline content (file
         absent at base ref)" — the pass was born in this window
```

**TTL-001 / triton-to-linalg** (single-repo, per goal §5) — `review
triton-to-linalg` against the triton-ascend index with `--docs-dir`/`--dir`
pointing at the harness-side docs: record `triton-to-linalg.md:111`, finding
TTL-001 (pass-field + entity_refs), 0 invariant guards in this index (honest — the
contract attribute is AscendNPU-IR-side). No cross-repo resolution attempted
(rejected, ADR-022/023).

## 4. Evidence retrieval examples

```
$ mlir-repomap evidence constraint:bishengir/…/AutoVectorizeV2.cpp:1406
ENTITY:  constraint:…:1406
ROWS:    1 (legality-guard evidence)
REF BY:  AV2-001 [evidence.ref], VFF-002 [evidence.file]
HISTORY: fa682a1a3 (fallback removal), 53a5d7498, 896d30c03, …
```

Exactly the goal's shape — Verifier evidence point, referenced-by findings, changed
commit — retrieved structurally: `matched_via` names the equality that produced the
link, so the agent can always audit why a finding appears.

## 5. Workflow changes

- **pass-analysis step 0 → "Compiler memory context"**: `review <pass>` is the
  memory lookup (previously reviewed? protected invariants? supporting evidence?
  what changed?); `finding-impact` follows for drifted findings; empty memory is a
  stated valid outcome.
- **pipeline-audit lens 1g "Historical contract memory lens"**: per stage,
  *previous contract* (review record / invariant guards) → *current change*
  (constraint-diff / file-commits since baseline) → *review requirement* (which
  protected invariants the change touches, which tests to re-run). The lens quotes
  memory; it never re-reviews or updates it.

## 6. Tests

42/42 (38 preserved + 4 new `ReviewMemoryTest`): review query joins all layers
(record verbatim, FI-001 via pass-field, FV-002 via entity_refs, fixture guard
`constraint:lib/SimpleFold.cpp:7`); recent-impact integration (drifted guard in the
controlled git repo surfaces as file-commits + constraint-diff inside the review);
evidence catalog (entity + rows + non-empty history + ref/file linkage positive with
cleanup + empty default linkage negative); missing-artifact negative (no dossier, no
findings → explicit "no review memory found" note; unknown entity → empty catalog,
never an error).

## 7. ADR/status changes

ADR-023 (design / data ownership / rejected: embedding memory, automatic review,
cross-repo validation); status.md Phase 17 section; roadmap unchanged priorities +
new limitation notes; query-api.md gains `review` and the evidence-catalog contract.

## 8. Remaining limitations

- Dossier location follows the documented `docs/compiler-architecture/passes/`
  convention; repos using another layout need `--docs-dir`.
- Record extraction is header-based ("# … Compiler Review …" to the next top-level
  header); dossiers without the header yield no record.
- `evidence.file` matching can over-match when several entities share one file —
  `matched_via` is always exposed so the agent can audit the link.
- Review resolves against one index; cross-repo artifacts are notes/uncertainty
  (rejected scope, ADR-022/023).
- The memory join reads the current dossier/findings docs; it does not history them
  (doc-layer versioning remains the repos' own git history).

## 9. Why this improves the Compiler Knowledge Evolution Loop

The loop's outputs are now *its own input*: what Phases 13–16 produced (review
records, findings, impact signals) is queryable as memory before the next analysis,
so every new pass-analysis starts from what the loop already learned instead of
re-deriving it. The remembered state is exactly the three-layer state — verbatim
agent reasoning (record), deterministic facts (guards, constraints), and structural
evidence links (catalog) — so memory cannot drift into the graph and the graph
cannot overwrite memory. Concretely: one `review` call replaces the four-surface
re-assembly (dossier scroll + findings list + per-finding impact + constraint
query), and every element of the answer carries its own dossier:line, file:line, or
commit evidence.
