# Pipeline Audit — triton-ascend Ascend flow (`make_ttgir` + `init_triton_ascend_passes_ttir`)

> Provenance: Phase 8 `pipeline-audit` workflow (provenance-aware). triton-ascend HEAD
> `8ba4ac4ce` · indexer v21 · 2026-09-05.

# Builder provenance

Two composition frontends build the same Ascend flow:

1. **Python (authoritative stage list)**: `third_party/ascend/backend/compiler.py`
   - `make_ttir` (:163-185): inliner → rewrite_tensor_descriptor_to_pointer → combine →
     canonicalizer → reorder_broadcast → cse → licm → symbol_dce → loop_unroll →
     `ascend.passes.ttir.add_graph_optimize(...)` → `pm.run(mod, 'make_ttir')`.
   - `make_ttgir` (:237-249 visible fragment): `convert_triton_distributed_to_hivm` →
     `triton_control_flow_opt` → `triton_to_structure` →
     `discrete_mask_access_conversion(compile_on_910_95, compile_mode)` →
     `triton_to_annotation` → `triton_to_unstructure` → **`triton_to_hivm`** →
     **`triton_to_hfusion`** → `triton_to_llvm` → `bubble_up_operation` →
     `triton_to_structure` (again) → `triton_to_linalg(...)`.
2. **C++ (registration)**: `init_triton_ascend_passes_ttir` (`triton_ascend.cc:62`,
   15 extracted stages; e.g. triton-to-annotation at order 4) — exposed for
   tooling/debugging; the compiler.py stage list is what production runs.

Each `ascend.passes.ttir.add_*` call resolves through `ADD_PASS_WRAPPER` bindings in
`python/src/passes.cc` to `create...Pass()` C++ factories — i.e. the chain
**Python builder → C++ wrapper → C++ pass factory → pass** is fully traceable by
hand today, but not by the graph (**EG-1**, the phase's headline gap).

# Dialect transition map (abstraction boundary)

| stage (Python) | dialect transition | abstraction note |
|---|---|---|
| make_ttir | triton (TTIR) → triton (optimized) | abstraction preserved |
| convert_triton_distributed_to_hivm | triton-distributed → **HIVM** (baseline dialect!) | first hardware-aware drop |
| triton_to_structure / unstructure | triton → triton_structured → back | shape/loop re-structuring |
| triton_to_annotation | triton_ascend.AnnotationOp → **bishengir annotation.mark** | cross-repo attribute handoff |
| discrete_mask_access_conversion | triton_ascend → triton_ascend | hardware access-pattern rewrite |
| **triton_to_hivm / triton_to_hfusion** | triton → **HIVM / HFusion** | the main handoff into the Phase 2-7 baseline stack |
| triton_to_llvm | triton → LLVM | second (competing) lowering frontier |
| triton_to_linalg | triton → **Linalg** (→ AscendNPU-IR stack) | third frontier |

**Answer to "when does Triton abstraction become Ascend hardware representation"**: three
distinct frontiers coexist — (a) HIVM/HFusion conversion inside `make_ttgir` (the
production Ascend path, handing over to the baseline repo), (b) LLVM via the upstream
path, (c) Linalg via `triton-to-linalg` (dossier: the 2319-line frontier pass). The
coexistence of (a) and (c) inside one stage list means the same kernel IR passes through
hardware-aware lowering **and** a Linalg re-materialization — an intentional double
representation whose sequencing contract lives only in the Python stage order.

# Hidden contracts found

1. **Annotation forwarding** — `triton_to_annotation` forwards arbitrary attributes into
   `annotation.mark` ops; the baseline stack's consumers (stride-align machinery) dispatch
   on those names. No schema check that forwarded names are known to the consumer repo
   (cross-repo contract, QG-7).
2. **compile_mode threading** — `compile_on_910_95` / `compile_mode` flow from Python
   options into multiple pass options (discrete_mask_access_conversion,
   triton_to_structure, triton_to_unstructure, triton_to_linalg); Python is the single
   source of these guards — invisible to C++-only analysis.
3. **double triton_to_structure** — the stage list calls `triton_to_structure` twice
   (:240, :248) around the HIVM/HFusion frontier; the second call's justification is not
   documented in the builder (audit question for the owners).
4. **`pm.run(mod, 'make_ttir')`** — stage completion marker; a natural (unused)
   verification hook per stage.

# Ordering justifications (swap outcomes)

- `triton_to_annotation` before `triton_to_hivm`/`triton_to_hfusion`: swap ⇒ annotations
  erased by conversion, baseline contracts (stride-align marks) never apply (silent).
- `discrete_mask_access_conversion` before `triton_to_hivm`: swap ⇒ hardware access
  patterns materialized at the wrong level (wrong lowering).
- `convert_triton_distributed_to_hivm` first: swap ⇒ distributed ops unhandled by the
  structure passes (compile error).
- `triton_to_linalg` after the HIVM/HFusion frontier: swap ⇒ Linalg re-lowering competes
  with already-hardware IR (double representation conflict).

# Verdict

The Ascend flow's authoritative builder is Python; the C++ registration function is a
subset view. Until EG-1 (Python pipeline extraction) lands, `repo pipeline` on
triton-ascend shows the C++ view only — audits must read `backend/compiler.py` stage
lists alongside the graph (this audit did both; every Python-side fact above carries
file:line evidence).
