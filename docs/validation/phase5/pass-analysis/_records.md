# Phase 5 Pass-Analysis Validation Records

One record per analyzed pass. Full dossiers:
`AscendNPU-IR/docs/compiler-architecture/passes/<file>`.
Query trace = the exact RepoMap commands used (all runs also start with `status`).

| pass (goal name) | dossier | query trace | queries out | files read | facts completeness | evidence quality |
|---|---|---|---|---|---|---|
| MergeVecScope | passes/merge-vec-scope.md | pass hfusion-merge-vf; pipeline bufferizationPipeline --brief | 4.4k B | MergeVecScope.cpp (targeted, ~900 of 1634 lines) | full 13-step; IR before/after from lit CHECK | file:line on all claims; 2 Potential correctness findings with code evidence |
| HFusionFlattenOps | passes/hfusion-flatten-ops.md | pass HFusionFlattenOps (miss → gap QG-2) → pass hfusion-flatten-ops; pipelines ×4 | 6.1k B | FlattenOps.cpp (141, full), Flattener.cpp header comment region, 4 test files | full; coverage dims explicit | strong; mode divergence documented from RUN lines |
| MarkStrideAlign | passes/mark-stride-align.md | pass hivm-mark-stride-align; tests | 2.9k B | MarkStrideAlign.cpp (1119, full), tests | full incl. output-invariant & delete-the-pass answer via enable dossier | strong; found same-name-builder merge (QG-1) while validating graph vs source |
| EnableStrideAlign | passes/enable-stride-align.md | pass hivm-enable-stride-align; alignStoragePipeline graph check | 2.4k B | EnableStrideAlign.cpp (813, targeted ~500), 2 test files | full; delete-the-pass answer concrete (metadata + runtime misalignment) | strong |
| AutoVectorizeV2 | passes/auto-vectorize-v2.md | pass hfusion-auto-vectorize-v2; pipeline hfusionAutoVectorizePipeline --brief; tests | 5.2k B | AutoVectorizeV2.cpp (1424, targeted ~350), test listing | full; supported/unsupported grounded incl. failure conditions | strong; transform-dialect design documented |
| VFFusion | passes/vf-fusion.md | pass VFFusion; pipeline membership | 2.1k B | PreVectorizationFusion.cpp (970, targeted ~300), VFFusion/Passes.td | full; VFFusion↔AV2 contract answered with direct code comment | strong; found stale-attr leak when AV2 off |

Observations common to all runs:

1. The skill→workflow→query path worked unchanged for all six passes (the Phase 4
   conventions were followed literally; no repo-wide grep was needed).
2. Identity resolution: 5/6 goal-name lookups succeeded; the miss (QG-2) degraded to one
   extra query, not a block.
3. `patterns: []` in every dossier (QG-3) is the biggest single facts-completeness hole;
   despite it, algorithm sections were reconstructable from source at evidence pointers.
4. Human-judgment spots (workflow worked but a human would double-check): Fixpipe
   hardware tables in mark-stride-align; transform-sequence details of AutoVectorizeV2;
   the "two bufferization rounds" intent in bufferizationPipeline.
