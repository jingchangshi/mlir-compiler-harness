# Phase 15 Validation — Attribute Creator Precision & Provenance Closure (RG-1)

Date: 2026-09-05 · harness @ Phase 14 (`13e3158`) · indexer v45 (full re-index both
repos: AscendNPU-IR 2951 files / 58 s, triton-ascend 1265 files / 16 s) · tests 32/32.

Question of the phase: **can the graph say who creates an attribute, where it is
attached, and who assumes its semantics — without guessing?**

Design basis: `docs/validation/phase15/attribute-provenance-gap.md` (current model,
missing information, TTL-001/TTA-001 cases). Architecture change: ADR-021.

## Architecture change summary

- New extractor `repomap/src/mlir_repomap/extractors/attribute.py`: for every
  `XxxAttr::name` / `kXxxAttr` reference, classify the **enclosing container**
  (brace-matched): pattern class (conversion base → `ConversionPattern`, else
  `RewritePattern`), op `build` method → `OpBuilder`, pass class/method → `Pass`,
  OpPassManager function building a pipeline → `PipelineBuilder`, free function taking
  `PatternRewriter&` → pattern-side helper (RewritePattern/ConversionPattern by
  signature — same rule style as the ADR-012 populator rule).
- **Mechanism is line-classified**: `XxxAttr::get(` = construction;
  `setAttr/addAttr/addAttribute` = attachment (`attach: true`); `getAttr/removeAttr/
  hasAttr` = read → consumer (`role: verifier` for verify methods, else reader). A
  mention alone never becomes a creator edge.
- Old containment-based `CREATES_ATTRIBUTE` block removed from cpppass.py — replaced by
  typed edges (creator lists deliberately shrink; see regression impact).
- New query `attribute-provenance <name>` (query.py + CLI + query-api.md): definitions
  (td AttrDef join + DIALECT_OWNS) / typed creators / typed consumers / file refs /
  explicit diagnostics; ambiguity explicit; definition-only attributes served from the
  td side. No new node kinds; no reasoning enters the graph.

## Example queries (real output, AscendNPU-IR @ v45)

**Typed creators across container kinds:**

```
$ mlir-repomap attribute-provenance TreeReductionSelectionFrozenAttr
creators:
  - type: Pass, attach: true, entity: pass:vf-fusion,
    evidence: VFFusionPass.cpp:168        # the VFFusion→AutoVectorizeV2 contract

$ mlir-repomap attribute-provenance MultiBufferAttr
creators:
  - type: RewritePattern, attach: true,
    entity: function:…/MarkMultiBuffer.cpp:mark, evidence: MarkMultiBuffer.cpp:238

$ mlir-repomap attribute-provenance AVE_VectorLayoutAttr     # definition-only
definitions: attr:AVE_VectorLayoutAttr @ HIVMAVEAttrs.td:345, dialect: AVE
diagnostics: ["no IR-level references found (definition-only attribute)"]
```

**Full chain (creator → consumers, TTL-001's contract attribute):**

```
$ mlir-repomap attribute-provenance StrideAlignDimsAttr
creators:  pattern:NormalizeAlignInfoPattern (RewritePattern, attach,
           EnableStrideAlign.cpp:98)
consumers: pass_class:ConvertHIVMToStandardPass (reader, HIVMToStandard.cpp:2083),
           pattern:AddAlignAnnotationMarkForAlloc (reader, :137),
           pattern:EnableAlignAllocation (reader, :366)
diagnostics: no TableGen AttrDef definition found (C++-level attribute)
```

## Finding enhancement (goal §6)

**TTL-001 — flatten→storage-align contract.** The finding's evidence chain is now
machine-checkable instead of a hand-quoted comment:

```
attribute creator                     flatten side
  pattern:NormalizeAlignInfoPattern     EnableStrideAlign.cpp:98 (attach)
        v
storage-alignment consumers           MarkStrideAlign assumes flattened shapes
  pattern:EnableAlignAllocation :366    (finding evidence :932-935, drift-checked)
  pattern:AddAlignAnnotationMarkForAlloc :137
        v
conversion boundary reader
  pass_class:ConvertHIVMToStandardPass  HIVMToStandard.cpp:2083
```

The finding's "no verifier spans the two repos" claim is now backed by the typed
consumer list: every consumer is a reader — **zero verifier-role consumers**, exactly
what the finding asserts.

**TTA-001 — annotation forwarding contract.** The three questions answered:
*Where created?* — triton-ascend references (MarkGMLoadPass.cpp, UBOverflowChecker.cpp)
are unattributed reads: no typed creator on the producer side (honest diagnostic, not a
guess). *Where forwarded?* — TritonToAnnotation.cpp:55 `markOp->setAttrs(op->getAttrs())`
is dynamic, name-agnostic forwarding: provable as the forwarding site, deliberately NOT
attributable per attribute. *Where validated?* — no verifier-role consumer in either
repo; validation remains the agent-run ecosystem contract check (Phase 11 machinery).
RG-1 therefore *sharpens* the finding: the contract risk is now stated as "creation
unattributed + forwarding dynamic + validation absent", each backed by a deterministic
result.

## Regression impact (v43 → v45)

The old CREATES_ATTRIBUTE was containment-based (any mention within a pass class's
200 lines = "created"). Creator lists shrank **by design**:

| attribute | v43 creators | v45 creators | verdict |
|---|---|---|---|
| MultiBufferAttr (AN) | 3 (plan-memory, mark-multi-buffer, cv-pipelining) | 1 — `mark()` helper (attach @ :238) | 2 false positives removed (`hasAttr`/`getAttr` reads) |
| InlinableQuantScaleAttr (TA) | pass_class:FixpipeOptPass | none typed | was a `hasAttr` read (:140) — false creator removed |
| SyncBlockLockUnorderedAttr (AN) | partial | `pass:hivm-insert-free-lock-var-before-return` (attach @ :131) | now typed + attach site |
| TCoreTypeAttr (AN) | partial | `pass:hivm-mark-real-core-type` (attach @ :158) | now typed + attach site |
| TreeReductionSelectionFrozenAttr | pass_class-level | `pass:vf-fusion` (attach @ :168) | resolved pass identity |

Ecosystem contracts (`ecosystem contract`) consume the same edges, so cross-repo
creator inventories are now mechanism-honest.

## Tests (goal §7)

32/32 pass — the Phase 14 suite (25) intact plus 7 new
(`AttributeProvenanceTest`): definition join + dialect ownership; all creator types
(OpBuilder/RewritePattern/ConversionPattern/PipelineBuilder/Pass) from a new fixture
file (`lib/SimpleAttrs.cpp` + td AttrDef); attach flags; verifier-as-consumer-not-creator;
explicit ambiguity; not-found. Ambiguous-creator handling is structural: distinct
containers yield distinct typed edges (each with its own evidence), and ambiguous
*queries* return `{"error":"ambiguous"}`.

## Architecture review (goal §8)

- **Q1 three-layer separation** — intact: creators/consumers are deterministic
  source-classified facts (container spans + line mechanisms); reasoning stays in
  dossiers/findings; findings only gain a machine-checkable evidence source.
- **Q2 risk of writing agent judgment into the graph** — none in this phase: every new
  edge is derived from a brace-matched container span and a classified source line;
  unprovable things (dynamic `setAttrs` forwarding, Python kwargs — no occurrence found)
  are deliberately absent and recorded as limitations.
- **Q3 does RG-1 reduce finding false positives?** — yes, measurably: the
  containment-based creator model produced false creators (MultiBufferAttr 3→1,
  InlinableQuantScaleAttr 1→0 typed, both verified against source as reads); typed
  consumers now separate readers from verifiers, so "who assumes the semantics" is no
  longer conflated with "who mentions it".
- **Q4 MCP / runtime graph still needed?** — no new evidence this phase: the new query
  served the workflow and finding validation through the CLI in ~1 call per attribute;
  runtime-level semantics remain out of scope. Deferred (evidence-based).

## Remaining gaps

- Attributes defined at C++ level (no td AttrDef — e.g. StrideAlignDimsAttr) surface as
  a diagnostic, not a definition (td join impossible without td).
- Dynamic forwarding (`setAttrs(op->getAttrs())`) is not per-attribute attributable —
  TTA-001's per-name chain stays open by design.
- Inline (non-qualified) `build`/`verify` methods in op class bodies are not scanned
  (only qualified definitions and class spans); ods-generated code is build-tree anyway.
- Python `Pass(..., attr=)` creator idiom: not observed in the validation repos — not
  implemented; will be added if an ecosystem repo shows it.
- Unattributed references remain file-level REFERENCES (counted, not guessed).
