# Phase 8 Extractor Gaps (goal §9 numbering)

## EG-1 — Python pipeline composition (headline gap)

`third_party/ascend/backend/compiler.py` `make_ttir`/`make_ttgir` are the authoritative
builders; passes are exposed via `python/src/passes.cc` `ADD_PASS_WRAPPER("add_x",
createXPass)` bindings and invoked as `ascend.passes.ttir.add_x(pm)`.
Impact: upstream Triton passes show no pipeline membership; the production stage order is
invisible to the graph (audits read the .py manually — see pipeline-audit/make-ttgir.md).
Generic solution (recorded, not implemented per phase rules): a Python/PyBind pipeline
extractor — (a) parse `ADD_PASS_WRAPPER` bindings into factory-reference edges;
(b) parse `make_*` functions' `passes.<group>.add_*(pm, ...)` call sequences into
file-qualified Python pipeline builder nodes (the generic "pipeline builder" abstraction
already exists — only the extractor is missing). Priority: **High** (ecosystem-wide).

## EG-2 — dialect-transition edges

TTIR→TTGIR→HIVM/HFusion/LLVM/Linalg transitions are visible only via pass dossiers.
Generic schema candidate (dialect-transition edge kind), deferred: both repos would
benefit, but no current workflow consumes it; the audit documented transitions manually
this phase. Priority: Medium, revisit with a consumer.

## EG-3 — registration idioms

Catalogued: bare generated-base inheritance in headers (FIXED this phase: RE_PASS_CLASS
accepts `(impl::)?XxxBase<`); C++-only `PassRegistration` families; upstream td without
`let constructor` (factory absent by design, ADR-001); factory suffix matching added for
dialect-prefixed classes; hardcoded kernel-name carve-outs in pass logic
(`pcb10_tc01_kernel` in merge-small-block — reported via dossier, not an extractor issue).

## Carried from the earlier Phase 8 pass (renumbered)

- runOnOperation-internal OpPassManager builders misclassified as pipelines → now part
  of the EG-1/EG-3 family (a pass method building a pipeline is a "pipeline builder"
  attached to the pass, not a standalone pipeline). Fix design unchanged; Priority Medium-High.
- gtest coverage extraction (was EG-5, now QG-8). Priority: Medium.
