# Phase 11 Validation — Cross-Repository Compiler Handoff Graph

Date: 2026-09-05 · triton-ascend HEAD `8ba4ac4ce` · AscendNPU-IR HEAD `5671889a3` ·
indexer v28 (per-repo) · harness tests 12/12.

Question of the phase: **can we understand compiler ecosystem handoffs?**

## Design (ADR-017)

Per-repo indexes stay untouched; a generic **ecosystem layer** (`ecosystem.py`,
`mlir-repomap ecosystem --repos A --repos B <status|handoff|boundary|contract> [name]`)
derives handoff records by matching artifacts by name across the two indexes:

- **Dialect handoff** (confirmed): consumer repo's `DIALECT_TRANSITIONS_TO` output
  dialect that is *defined* in the producer repo. Evidence: the ConversionTarget line
  in the consumer's pass.
- **Operation handoff** (confirmed): consumer repo's `PATTERN_CREATES_OP` op that is
  *defined and dialect-owned* in the producer repo; op index keyed by both TableGen
  class name and mnemonic (a real matching bug found and fixed during validation:
  `op:MarkOp` vs mnemonic `mark`).
- **Cross-repo attribute contract**: attribute names referenced in both repos, with
  per-repo creators and reference counts.
- Repository identity = index path (display name = basename) — no semantic repo names
  in the engine.

## Validation results (triton-ascend ↔ AscendNPU-IR)

### Dialect handoffs (confirmed, 2)

| consumer | artifact | via pass | producer |
|---|---|---|---|
| triton-ascend | `dialect:Annotation` | `pass:triton-to-annotation` | AscendNPU-IR |
| triton-ascend | `dialect:HIVM` | `pass:triton-to-hivm` | AscendNPU-IR |

### Operation handoffs out of triton-ascend (10+)

`op:MarkOp` → owned by `dialect:Annotation` (via triton-to-annotation,
TritonToAnnotation.cpp:53, confirmed); `op:YieldOp`/`op:LoadOp`/`op:StoreOp` →
AscendDPX; `op:AtomicRMWOp` → HIVM; `op:HistogramOp`/`op:Conv1DOp`/`op:Conv2DOp`/
`op:IndirectStoreOp` → HFusion. These are the concrete "Triton hands the IR to the
AscendNPU-IR stack" edges.

### Cross-repo attribute contracts (5)

`HIVMTightlyCoupledBufferAttr` (B ref 1 / A ref 13), `TCoreTypeAttr` (B 6 / A creators
+ 13), `MultiBufferAttr` (A creators hivm-plan-memory, cv-pipelining), `SyncBlockLockUnorderedAttr`,
`InlinableQuantScaleAttr`. Who owns the contract: the repo with confirmed creators owns
production; the other side consumes.

### Boundary view

`ecosystem boundary triton-ascend` returns the complete handoff picture: 2 dialect
consumptions + 10 op handoffs + 5 attribute contracts — the "Triton hands the IR to
AscendNPU-IR" statement is now a query with evidence.

## Workflow changes

- `pass-analysis.md` step 7c: cross-repository contract (producer/consumer/handoff
  contract) when an ecosystem index is available.
- `pipeline-audit.md` lens 1z: ecosystem boundary lens (repository pipeline → external
  compiler stage → next repository).

## Honest limitations

- Handoff matching is name-based across indexes; renamed artifacts across repo versions
  produce missed handoffs (no versioned artifact identity).
- The ecosystem layer computes at query time (no persistence) — fine at this scale.
- Runtime/binary-level handoffs (executed kernels, runtime APIs) are out of scope.
