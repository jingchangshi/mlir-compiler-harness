# Phase 9 Validation — Cross-language Compiler Pipeline Provenance

Date: 2026-09-05 · triton-ascend HEAD `8ba4ac4ce` · AscendNPU-IR HEAD `5671889a3` ·
indexer v28 · harness tests 12/12.

Question of the phase: **can compiler construction be traced across languages?**

## Implemented (ADR-015, all generic)

1. **Binding boundary entity** (`binding:<name>`): PyBind-style boundaries — `m.def("name",
   ...)` with brace-matched lambda bodies (factory found inside) or direct function
   references. `BINDING_MAPS_TO` edges.
2. **Python pipeline-composition functions**: identified by signature/body (pass-manager
   parameter/usage), never by name; `PYTHON_COMPOSES` edges from stage calls
   (`passes.<group>.add_*(pm, ...)`) to bindings. Python parsing via stdlib `ast`
   (end_lineno spans); BOM stripped (vendor files carry U+FEFF — found during validation).
3. **Resolution chain**: PYTHON_COMPOSES → binding → BINDING_MAPS_TO → factory →
   BINDING_EXPOSES_PASS → pass. New query `pipeline-composition <pass>`.
4. **Pipeline-kind correctness** (Phase 8 EG carried): `runOnOperation`/`initialize`
   bodies no longer become pipeline nodes; RegBase builders verified intact.

## Validation results

- triton-ascend full chain: `ttir_to_linalg` (compiler.py) → `add_triton_to_linalg`
  (triton_ascend.cc:84) → `createTritonToLinalgPass` → `pass:triton-to-linalg` — every
  hop file:line. Same for triton-to-annotation (cc:80) and 13 more chains
  (pipeline-composition-map.md).
- AscendNPU-IR regression: runOnOperation pipeline nodes 0 (was: InlineScope 20-stage
  mislabel); buildBiShengHIRPipeline / buildHFusionRegBasePipeline intact; index 52 s.
- "Why here" re-analysis: triton-to-linalg & triton-to-annotation dossiers updated —
  the question "why does this pass appear here" is now answerable from one query instead
  of reading Python source.

## Remaining gaps

- Composer detection is usage-based: a helper that takes `pm` but isn't a stage list
  could be misattributed (mitigated: nodes carry the pm.run marker when present).
- `pm.run(...)` stage-completion markers are recorded as node summary text, not edges —
  a future "stage verification" edge candidate.
- Non-PyBind binding styles (SWIG/ctypes) unmodeled — none observed in the ecosystem.
