# AscendNPU-IR vs triton-ascend — Comparison

## Same (generic engine, both repos, zero repo-specific code)

| capability | AscendNPU-IR | triton-ascend |
|---|---|---|
| td Passes.td + `let constructor` → confirmed factory | ✓ (18 td files) | ✓ (Ascend side, e.g. triton-to-linalg) |
| pattern population chains (populate* → patterns.add) | ✓ 142 passes with chains | ✓ (e.g. TritonToLinalg canonicalization family) |
| cross-file dialect ownership | ✓ (inferred prefix heuristic) | ✓ (direct Op<Dialect> style) |
| attribute entities + creator/consumer | ✓ (86 attrs in triton-ascend / 40+ in baseline) | ✓ |
| pipeline-builder provenance | ✓ | ✓ (init_triton_ascend_passes_ttir @ triton_ascend.cc:62) |
| lit-test feature tags | ✓ | ✓ (184 test files) |

## Different (idioms)

| dimension | AscendNPU-IR | triton-ascend |
|---|---|---|
| pass class location | cpp file, `impl::XxxBase<>` | header, bare `XxxBase<>` (EG-4, fixed) |
| op TableGen style | `Xxx_Op` multiclass aliases | direct `Op<Dialect,...>` |
| C++-only passes | rare (711 PassWrapper refs but td-first) | ComputeBlockOpt family via PassRegistration |
| factory availability | always (`let constructor`) | upstream td has none (generated; ADR-001 ⇒ absent) |
| pipeline composition | C++ builders only | C++ + **Python stages** (EG-3) |
| test style | lit RUN .mlir | lit + C++ gtest (EG-5) |

## Missing / to improve

1. EG-3 Python pipeline composition — the real TTGIR pipeline is invisible; a Python
   pipeline-composition extractor would serve the whole Triton ecosystem (candidate next).
2. EG-5 gtest coverage — C++ unit tests exist but produce no TEST edges.
3. EG-1 runOnOperation-internal pipeline builders mislabeled as pipelines.
4. Cross-repo handoff edge: triton-ascend → AscendNPU-IR type contract (hfusion ops) is
   not modeled — the two graphs are separate indexes by design; a "handoff dialect"
   annotation would connect them (deferred; needs a real consumer).
