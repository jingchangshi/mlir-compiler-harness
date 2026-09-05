# Phase 14 Validation — Compiler Knowledge Evolution Loop

Date: 2026-09-05 · harness commit at phase start `6bf4f97` · AscendNPU-IR HEAD
`5671889a3` · triton-ascend HEAD `8ba4ac4ce` (both = finding baselines) · tests 25/25.

Question of the phase: **can the harness remember compiler evolution — findings,
their lifecycle, and the commits that affected them — without polluting the facts
graph and without ever auto-judging a fix?**

## 1. Finding Schema (goal §4)

Doc-layer artifact, not a graph entity. One YAML file per finding
(`<ID>.yaml`) in `docs/compiler-architecture/findings/` of the repo it concerns
(triton-ascend findings live harness-side, mirroring the Phase 8 doc placement).
Core fields per the goal sketch: `id / category (correctness|coverage|performance|
architecture|opportunity) / pass / statement / evidence / reasoning / status /
created_at`, plus `evidence[].ref` (optional link to a deterministic graph node),
`history` (lifecycle log), `regression` (Compiler Regression Memory), and
`review.baseline_commit` (target-repo HEAD at creation). Full contract:
`docs/architecture/query-api.md` §Finding artifacts. Parser: strict YAML subset,
stdlib-only, fail-soft — invalid documents surface in `diagnostics` and never
break a listing (validated: flow style, tabs, missing fields all rejected).

## 2. Lifecycle Model (goal §5)

`open → acknowledged → in-progress → resolved | rejected | superseded`.
Enforced deterministically by `validate_finding`: every history entry requires
`reason` **and** (`evidence` or `reference`); `resolved/rejected/superseded`
require a matching history entry; `superseded` requires `superseded_by`.
History is append-only. The engine has no API to advance a status — only agents
edit the document (three-layer separation preserved: graph facts / agent
reasoning / evidence pointers, ADR-019 → ADR-020).

## 3. Git Integration (goal §6)

`FindingService` (`repomap/src/mlir_repomap/findings.py`, CLI `findings
list|check|show`) implements deterministic drift tracking:

- **Evidence changed**: for each evidence item with a `snippet`, the service
  verifies the text is still present at the recorded location (window ±15 lines
  around `lines`), elsewhere in the file ("moved"), or gone ("missing" →
  `evidence_changed`, e.g. an old `return failure();` replaced by a new legality
  check). Deleted/renamed evidence files are flagged directly.
- **Finding affected**: `git log <baseline>..HEAD -- <evidence-file>` per
  evidence file; every commit becomes a "possibly affected" pointer. Output in
  the goal format:

  ```
  Finding TTL-001
  possibly affected by commit 6ff6d725a ([TritonOP](feat) Add al.conv2d op (#1819)) (+1 more)
  Needs review
  ```

- `--since REF` overrides the recorded baseline; findings without a baseline are
  reported `unchecked` with instructions (never silently skipped). Cross-repo
  evidence (`repo:` field) is noted, not drift-checked. The service never
  updates status — "Needs review" is a report, not a mutation.

## 4. Historical Review Validation

Real-history drills (finding baselines are today, so `--since` replays what a
long-lived memory would have flagged):

| drill | result |
|---|---|
| AscendNPU-IR `--since 4ddead06f` (MergeVecScope A5 migration) | all 5 findings flagged; AV2-001/VFF-002 point at `fa682a1a3` (the exact fallback-removal commit recorded in AV2-001's regression memory), MVS-001/MVS-002 at `7875b76ea`, VFF-001 at `88d98b6b1` ([VFFusion] insert_slice fusion change) |
| triton-ascend `--since 2bafba14a` | TTL-001 flagged with 2 real commits (`6ff6d725a`, `a674a6f85`); **TTA-001 correctly clean** — no commit touched TritonToAnnotation.cpp, a true negative |
| baseline check (no `--since`) both repos | 7/7 clean, 9/9 snippets verified present — honest "no drift since creation" |

Unit tests (`repomap/tests/test_findings.py`, 13 cases) cover the same three
signals on a synthetic git repo: commit-on-evidence → needs review; snippet
replaced → `evidence changed`; no-baseline → explicit unchecked.

## 5. AscendNPU-IR Results (goal §9)

5 durable findings seeded from the Phase 13 review records, all status `open`
(created this session; transitions await their owners):

| id | category | statement (short) | regression memory |
|---|---|---|---|
| MVS-001 | correctness | single-use-VF assumption unguarded (comment-only, MergeVecScope.cpp:631) | ported from A5 (4ddead06f), risk medium |
| MVS-002 | opportunity | cross-block memref deps invisible → level-2 coverage lost | — |
| AV2-001 | correctness | verifier completeness unguarded behind the acceptance guard (:1406) | fallback crash fix 7875b76ea + fallback removal fa682a1a3, risk medium |
| VFF-001 | architecture | CCEC backend constraint coupled into frontend fusion guards | bitwise-ops fix dfa37a500, risk medium |
| VFF-002 | opportunity | `_fused_` outlining re-inlined downstream (AV2 :1379-1390) | — |

Every evidence pointer was re-verified against the current worktree (the Phase 13
dossier cited MergeVecScope.cpp:619-621 for the single-use comment; it now lives
at :631 — exactly the drift this phase mechanizes; the finding records the
re-verified location).

## 6. triton-ascend Results (goal §9)

2 durable findings: **TTL-001** (flatten-before-storage-align cross-dialect
contract, with evidence on BOTH repos — consumer assumption at AscendNPU-IR
MarkStrideAlign.cpp:932-935 marked `repo: AscendNPU-IR`, producer 1-D collapse in
TritonToLinalgPass.cpp:742) and **TTA-001** (forwarded attribute names
unvalidated, TritonToAnnotation.cpp:55 + the pass's only legality guard :69).
TTL-001 exercises the cross-repo evidence design end-to-end: local drift check
runs, external pointer is reported as a note.

## 7. Remaining Gaps

- Engine constraint line numbers can be off by one (`pass-constraints` reports
  TritonToAnnotation.cpp:69; the guard sits at :68) — snippet normalization
  tolerates it, but the constraint extractor's line anchoring deserves a look.
- `--since` needs a baseline strategy when findings predate the mechanism
  (workaround exists; a "last-audit ref" convention would help).
- Finding→commit attribution is file-granular; line-range attribution needs a
  semantic backend (clangd, still deferred).
- Lifecycle updates are manual by design; no automation was added (goal §10).

## 8. Next Phase Recommendation (goal §11.4)

**A — Attribute creator precision (RG-1)**: it strengthens finding evidence
(creator-side ownership for the 5 ecosystem contracts behind TTL-001/TTA-001),
completes the last provenance gap with an active workflow consumer, and does not
require new infrastructure. B (runtime contract graph), C (MCP), D (benchmark
intelligence) remain deferred — no blocking evidence this phase (see roadmap).

## Architecture review answers (goal §11.1–11.3)

1. **Should findings be stored long-term?** Yes — as doc-layer YAML in the target
   repo, engine-validated but engine-unowned. They survive re-indexing (the graph
   rebuilds; findings don't), they carry agent reasoning that must never live in
   the facts layer, and their value compounds with git history.
2. **Is the finding/graph boundary clear?** Yes: findings may *reference* graph
   nodes (`evidence[].ref`) but nothing flows back — no finding-derived edges, no
   status in the graph, no resolution judgment by the engine. The only engine
   duties are validation and deterministic drift reporting.
3. **Which resolutions can be auto-assisted?** Already automatic: drift
   detection, snippet verification, true-negative filtering (TTA-001).
   Assistable next: test-coverage cross-check via TEST_COVERS_PASS churn,
   constraint re-extraction diff as a finding-affected signal, ecosystem
   contract validation for TTA-001 (Phase 11 machinery). Never automatic:
   deciding a finding is resolved.
