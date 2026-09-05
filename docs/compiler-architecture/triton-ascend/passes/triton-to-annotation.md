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
