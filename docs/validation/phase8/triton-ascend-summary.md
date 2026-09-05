# Phase 8 Validation — Ascend Compiler Ecosystem (triton-ascend)

Date: 2026-09-05 · triton-ascend HEAD `8ba4ac4ce` · indexer v21 · harness tests 12/12 ·
0 parse diagnostics on the new repo.

## Scope

ZCode + harness migrated to a **different Ascend compiler repository**: triton-ascend
(Triton frontend + TTIR/TTGIR/LLVM path + Ascend TritonToLinalg path). Baseline
AscendNPU-IR stays as the validated comparison repo (nested inside triton-ascend at
`third_party/ascend/AscendNPU-IR/` and excluded from its corpus). Architecture docs for
the new repo: `docs/compiler-architecture/triton-ascend/` (in the harness repo — the
target is a GitHub clone the harness does not own).

## What worked with zero repo-specific code

- Indexing: 1255 files, 11 s, 1.5 MB; 8 dialects / 144 passes / 26 pipelines / 155
  patterns / 132 ops / 184 tests / 0 diagnostics.
- repo-map workflow end-to-end: six architecture docs generated (repository/dialect/
  pipeline maps, pass catalog, pattern-map, attribute-map).
- Provenance queries cross-repo: `pattern-owner FoldScanOffsetAddPtrChain` →
  `pass:triton-to-linalg` (after EG-4 fix); `pipeline-builder init_triton_ascend_passes_ttir`
  → `triton_ascend.cc:62` (confirmed); attribute entities from the `k*Attr` idiom.
- Pass analyses: 3 dossiers (lowering `triton-to-linalg` 2319 lines, optimization
  `merge-small-block` C++-PassRegistration idiom, upstream-idiom probe
  `tritongpu-accelerate-matmul`).

## Idioms encountered (Same / Different / Missing)

Same as AscendNPU-IR: td Passes.td with `let constructor`; `populate*` pattern populators;
`OpRewritePattern` family; attribute `*Attr::name` references; lit RUN tests.
Different: pass classes declared in **headers** inheriting bare (non-`impl::`)
`XxxBase<T>` (EG-4, fixed generically); C++-only `PassRegistration` families
(ComputeBlockOpt) without td; upstream td **without** `let constructor` (factory correctly
absent, ADR-001); upstream direct `Op<Dialect,...>` defs vs AscendNPU-IR's `Xxx_Op`
multiclass aliases.
Missing (gaps, not implemented per phase rules): Python-side pipeline composition
(EG-3), gtest test-coverage extraction (EG-5), runOnOperation-internal pipeline builders
misclassified as pipelines (EG-1), upstream factory-suffix matching added generically
(small, kept).

## Extractor gaps found (extractor-gaps.md)

EG-1 runOnOperation pipelines mislabel · EG-2 upstream factory absent by design
(documented, not a bug) · EG-3 Python-composed pipelines invisible · EG-4 bare
generated-base inheritance (FIXED) · EG-5 gtest coverage extraction missing.

## Answer to the phase question

Yes — the harness (engine + provenance graph + workflows + ZCode adapter) transfers to a
second Ascend compiler repository with **two small generic fixes and zero triton-specific
code**. The Ascend ecosystem pair now covers the full stack: Triton frontend → TTIR/TTGIR
(triton-ascend) → Linalg/AscendNPU-IR → HIVM lowering (AscendNPU-IR baseline).
