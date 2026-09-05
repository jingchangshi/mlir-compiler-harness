# RG-1: Attribute Provenance Gap — current model vs. needed precision

Phase 15 design document (Step 1/2 of the phase goal). Status quo reproduced from the
current index (AscendNPU-IR @ 13e3158 harness / 5671889a3 target, indexer v43).

## Current model (what the graph answers today)

| question | answerable today? | via |
|---|---|---|
| Attribute X exists | yes | `attribute:<X>` node (from `XxxAttr::name` / `kXxxAttr` idiom hits, cpppass.py) |
| X belongs to dialect Y | yes (definition side only) | `attr:<X>` td node + DIALECT_OWNS (tablegen.py RE_ATTRDEF) — but **not joined** to the reference entity |
| X appears in pass Z | yes, pass classes only | CREATES_ATTRIBUTE, source restricted to `pass_class:*`, naive 200-line containment from the class header, confidence inferred |
| **Who creates X?** | **no** | creator_type does not exist; a pass reference is indistinguishable from a pattern's or a builder's |
| **Where is X attached?** | **no** | no attachment signal (setAttr vs read) on any edge |
| **Which lowering boundary depends on X's semantics?** | **no** | verifier/pattern reads are only file-level REFERENCES (heuristic) |
| **Which transformation assumes X?** | partial | ecosystem contracts (`ecosystem contract`) list cross-repo reference counts, but creators were empty for 2 of the 5 contracts (e.g. HIVMTightlyCoupledBufferAttr: `creators: []` in both repos) |

Reproduced limitation: `mlir-repomap attribute StrideAlignDimsAttr` returns the
reference-entity node (heuristic role summary) + file-level REFERENCES edges + pass-class
CREATES_ATTRIBUTE edges — it cannot say that the attribute's *definition* lives in a td
file under a specific dialect, nor which pattern/pipeline creates it.

## Missing information (the gap, in the goal's terms)

1. **Creator identity and type.** The same textual signal (`XxxAttr::name` reference)
   means different things depending on the enclosing container: a RewritePattern building
   ops with the attr, an op `build` method defaulting it, a pass attaching it, a pipeline
   builder threading it. Today all of this collapses into "pass_class or nothing".
2. **Attachment sites.** `op->setAttr(FooAttr::name, ...)` is the ATTACHED_TO fact; it is
   not distinguished from a guard that merely reads the name.
3. **Definition join.** `attr:<X>` (TableGen) and `attribute:<X>` (IR references) are
   separate kinds; the provenance chain definition → dialect → creator → consumer is not
   one query.
4. **Verifier semantics dependency.** Verifier code that asserts an attribute's presence
   or shape is the strongest "who assumes this semantics" signal, and it is currently
   invisible (file-level heuristic only).

## Real cases: how RG-1 strengthens the Phase 14 findings

### TTL-001 (flatten-before-storage-align cross-dialect contract)

The finding's consumer-side evidence is MarkStrideAlign.cpp:932-935 ("directly treats
the Op as already having undergone the axis merging operation"). What the finding cannot
say today: **which attribute carries the alignment contract, who creates it, and where it
is attached** — the chain `attribute creator → flatten pipeline → storage-alignment
consumer` is exactly the creator-provenance chain RG-1 adds. With creator typing, the
storage-align consumer's `StrideAlignDimsAttr` chain becomes queryable end-to-end
(definition in HIVM td → creator container (typed) → MarkStrideAlign consumer), so the
finding's "no verifier spans the two repos" claim gains a machine-checkable inventory of
the attribute contracts on that boundary instead of a hand-quoted comment.

### TTA-001 (forwarded annotation attribute names unvalidated)

The finding says forwarded names are never validated against the consumer inventory.
RG-1 turns that inventory into provenance: for each forwarded attribute, `where created`
(creator container + evidence in triton-ascend), `where forwarded`
(TritonToAnnotation.cpp:55 `setAttrs` — an attach: true site), `where validated`
(consumer side: verifier/contract edges or the honest "no validating consumer found").
Today the answer to all three questions is "not in the graph".

## Design (Step 2) — what enters the graph and what does not

Principles: attribute stays a graph fact; only source-provable statements become edges;
agent judgment stays in dossiers/findings (ADR-019/020 untouched).

- **Creator typing is container classification** (deterministic, from the enclosing
  brace-matched body): pattern class with a conversion base → `ConversionPattern`;
  other rewrite-pattern bases → `RewritePattern`; op out-of-line `build` method →
  `OpBuilder`; pass class or its out-of-line method → `Pass`; pipeline builder function
  → `PipelineBuilder`. All six goal types are supported except **Verifier as a creator**:
  a verifier does not create attributes, it constrains them — recording it as a creator
  would be a false fact. Verifiers (and other read-only containers) are recorded as
  **consumers** (`REFERENCES` from the container with `role: verifier|reader`).
- **Attachment** is line-classified: a reference line containing `setAttr(`/`addAttr(`
  yields `attach: true` (confirmed at the line level); creation via `XxxAttr::get(`
  is recorded on the same typed edge.
- **Definition join** happens at query time (`attr:<X>` exact-name match + its
  DIALECT_OWNS edges) — no new node kinds, no schema growth beyond edge props.
- **Not implemented (no source evidence of the idiom):** Python `Pass(..., foo_attr=)`
  kwargs — no occurrence in the validation repos' composition code; recorded as a
  non-implemented pattern, not a silent omission.
- **Unattributable references** (no enclosing container) keep today's file-level
  REFERENCES behavior and are counted (`unattributed_refs`) in the query output —
  diagnostics, not guesses.

Consequence for the phase-14 loop: `findings` evidence pointers for TTL-001/TTA-001 can
cite `attribute-provenance` output as machine-generated evidence; the drift checker
verifies the snippets underneath it as with any evidence.
