# Phase 13 Validation — Compiler Review Intelligence Layer

(goal text numbers this Phase 11; directory follows the harness sequence — phase11/ is
the handoff validation, phase12/ the intent/constraint substrate.)

Date: 2026-09-05 · both repos at previously recorded HEADs · indexer v43 · tests 12/12.

Question of the phase: **can the harness assist compiler engineering decisions —
without polluting facts with judgment?**

## Review model (ADR-019): three strict layers

1. **Graph facts** — deterministic, engine-owned (constraints, boundaries, provenance).
2. **Agent reasoning** — dossier-layer review records, every judgment citing layer-1
   evidence and labeled as reasoning. Never written to the graph.
3. **Evidence pointers** — the `file:line`/query links connecting 1 and 2.

Review record format (workflow-defined, doc-layer): Pass · Intent · Protected
Invariants (each tied to its enforcing HAS_CONSTRAINT or marked **UNGUARDED**) ·
Constraints · Tradeoffs · Risks · Optimization Opportunities (Current / Evidence /
Protected invariant / Lost opportunity / Possible direction).

## Validation — five review records produced

| pass | guarded invariants | unguarded invariants (top findings) | opportunities recorded |
|---|---|---|---|
| hfusion-merge-vf | merged-func validity (2 verify guards), dep-ordering (partial) | **single-use VF assumption has no guard** | region-aware dependency closure → level-2 coverage |
| hfusion-auto-vectorize-v2 | verifier acceptance + clone transaction, attr cleanup | verifier completeness (expensive-checks off) | verifier rule inventory + multi-user fixtures |
| vf-fusion | 4 generalization legality-guards | backend constraint coupled into frontend pass (FP8/i1) | shared fusion cost model with AV2 |
| triton-to-linalg | descriptor-handoff validation, kernel classification order | flatten-before-storage-align cross-dialect contract | axis-identity metadata through flatten |
| triton-to-annotation | verbatim attribute forwarding, partial-conversion failure | forwarded attr names unvalidated vs consumer contract | ecosystem contract validation |

The **unguarded invariant** findings are the phase's signature result: they are visible
only by joining deterministic constraint facts with agent knowledge of the contract —
exactly the human-review insight the harness aims to scale.

## Workflow changes

- pass-analysis step 7f: Compiler Review Record (4 questions, unguarded-invariant
  emphasis).
- pipeline-audit lens 1x: cross-pass optimization flow ledger (creates/blocks/tradeoff,
  each entry citing evidence).

## Schema decision

No core-schema change (goal §9): review records live in dossier docs (reasoning layer).
Persistence as a separate review-record store would only be justified if cross-session
querying of reviews becomes a real workflow — noted, not needed now.

## RG-1 status

Not blocking: attribute ownership across the 5 ecosystem contracts was resolved by
agent reasoning (creators confirmed in Phase 11 records); stays backlog.
