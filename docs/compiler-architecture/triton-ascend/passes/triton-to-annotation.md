# triton-to-annotation (TritonToAnnotation) — triton-ascend

> Provenance: Phase 8 validation, `pass-analysis` workflow (backend/attribute case).
> HEAD `8ba4ac4ce` · indexer v21. Primary files:
> `third_party/ascend/lib/TritonToAnnotation/TritonToAnnotation.cpp` (76 lines),
> `third_party/ascend/include/TritonToAnnotation/Passes.td:10`.

# Overview

The smallest dialect transition in the Ascend flow — and the **cross-repository handoff
made concrete**: it rewrites `triton::ascend::AnnotationOp` into
`annotation::MarkOp` from the **bishengir Annotation dialect** (the AscendNPU-IR baseline
repo, reachable here as the nested checkout `third_party/ascend/AscendNPU-IR/`). After
this pass, Triton-level annotations are the same `annotation.mark` contract the baseline
stack's stride-align/enable machinery consumes (see baseline dossiers
`mark-stride-align.md` / `enable-stride-align.md`).

# Pipeline Context

- `init_triton_ascend_passes_ttir`, order 4 (C++ registration function,
  `triton_ascend.cc:62`); also invoked from the Python `make_ttgir` stage list as
  `ascend.passes.ttir.add_triton_to_annotation(pm)`
  (`third_party/ascend/backend/compiler.py:242`) — one pass, two composition frontends.
- Upstream: triton::ascend IR carrying AnnotationOps; downstream: annotation dialect IR
  entering the HIVM/HFusion flow.

# Registration

`def TritonToAnnotation : Pass<"triton-to-annotation", "mlir::ModuleOp">` with
`let constructor = "mlir::triton::createTritonToAnnotationPass()"` (Passes.td:10);
generated base `impl::TritonToAnnotationBase` (GEN_PASS_DEF :29).

# Input / Output Contract

- Input: `triton::ascend::AnnotationOp` instances anywhere in the module.
- Output: `annotation::MarkOp` at the same insertion point, **all attributes forwarded**
  (`markOp->setAttrs(op->getAttrs())`, TritonToAnnotation.cpp:47) — the attribute payload
  is the contract; consumers in the baseline repo dispatch on those attribute names
  (e.g. stride-align marks).

# Algorithm

`applyPartialConversion` with a single `OpRewritePattern`
(`TritonAnnotationConversionPattern`, :39-53) against a ConversionTarget legalizing only
the AnnotationDialect. Pattern provenance: direct `patterns.add` inside `runOnOperation`
(method-body container) → confirmed edge to `pass:triton-to-annotation` — resolved with
zero heuristics after the EG-4 fix (class declared with `impl::TritonToAnnotationBase`).

# IR Examples

```mlir
// BEFORE                                  // AFTER
%0 = triton_ascend.annotation %arg         annotation.mark %arg {<forwarded attrs>}
      {some_attr = ..., ...}                   : <same type>
```

SSA change: the annotation op is erased; its source value gains a mark user. Legality:
1:1 op replacement with forwarded attrs — no value semantics change.

# Attribute Contract

This pass is a pure **attribute forwarder**: it creates no attribute names itself but is
the bridge that makes baseline-repo attribute contracts apply to Triton-originated IR
(`repo attribute StrideAlignDimsAttr` chains in the baseline start here for triton
kernels). Attribute provenance beyond name level (which attrs actually flow) requires
value tracking — RG-1 territory, backlog.

# Potential Issues

1. **[Architecture | Potential]** Cross-repo include (`bishengir/Dialect/Annotation/...`)
   couples the two indexes; the harness models each repo separately, so the handoff
   dialect appears as an *external* dependency here (query gap QG-7).
2. **[Coverage | Potential]** No dedicated lit test found linking this pass by arg name;
   coverage is end-to-end via the triton→ascend kernel tests.

# Phase 9: Cross-language Composition ("why here")

`repo pipeline-composition triton-to-annotation`: Python composer `ttir_to_linalg`
(`backend/compiler.py`) -> binding `add_triton_to_annotation` (triton_ascend.cc) ->
`factory:createTritonToAnnotationPass` -> this pass. The pass sits at stage order 4 of the
C++ registration and before `triton_to_hivm` in the Python stage list because the baseline
stack's annotation consumers require marks to exist before HIVM lowering -- now
evidenced by both composition frontends from one query.

# Phase 10: Semantic Boundary

`repo boundary triton-to-annotation` (indexer v35):

- input dialect: `TritonAscend` (inferred — pattern matched ops ownership)
- output dialect: `Annotation` (**confirmed**, TritonToAnnotation.cpp:64
  `target.addLegalDialect<annotation::AnnotationDialect>()`)
- transition pair: `TritonAscend → Annotation`
- created ops: `annotation::MarkOp` (all attributes forwarded — the semantic contract
  is the attribute payload, consumed by the baseline repo's stride-align machinery)

This is the cleanest semantic boundary in the Ascend flow: a one-op dialect transition
whose entire meaning is the attribute contract.
# Phase 12: Intent & Constraints

- intent (graph): label **"lowering/conversion boundary" (inferred)** — TritonAscend →
  Annotation transition (Phase 10). Constraint: 1 legality-guard — partial-conversion
  failure (signalPassFailure if any AnnotationOp remains unconverted).
- agent interpretation: the pass exists to make Triton-originated annotations legible to
  the AscendNPU-IR baseline contract machinery (stride-align etc.); its constraint set is
  intentionally minimal because the semantic payload travels in attributes, not ops.

- query facts: intent_label={'label': 'lowering/conversion boundary', 'confidence': 'inferred'}; constraints={'legality-guard': 1}
  - `legality-guard`: failed(applyPartialConversion(module, target, std::move(patterns (third_party/ascend/lib/TritonToAnnotation/TritonToAnnotation.cpp:69)

# Compiler Review (Phase 13 — review record, agent layer)

- **Why does this pass exist?** To translate Triton-originated annotations into the
  baseline repo's attribute-contract machinery (`annotation.mark`) — the smallest
  cross-repo handoff with the largest semantic leverage.
- **Protected invariants & enforcing constraints:** attribute payload forwarded
  verbatim (code-guaranteed); partial conversion fails the pass (1 legality-guard).
  **UNGUARDED**: forwarded attribute names are not validated against the consumer
  repo's contract inventory (Phase 11 attribute map is the check, run by agents only).
- **Optimization opportunity (record):**
  Current behavior: unknown attribute names pass through silently. Evidence: 76-line
  pass, no name validation. Protected invariant: forward-compatibility. Lost
  opportunity: early detection of contract drift between repos. Possible direction:
  ecosystem contract validation (compare against AscendNPU-IR attribute-map).
- **Extension direction:** QG-7 external-dialect declarations + contract validation.
