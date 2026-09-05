# Phase 8 Extractor Gaps

## EG-1 — runOnOperation bodies that build OpPassManagers are classified as pipelines

Example: `ComputeBlockOptPass.cpp` runOnOperation (25 extracted "stages"), AddDynamicCVPipeline.
Impact: pipeline list contains pass implementations; audit queries by builder return pass
bodies. Generic fix: exclude functions named runOnOperation/initialize from pipeline-node
creation (they are pass methods; keep their contained edges attached to the pass).
Priority: Medium-High (visible in the top pipelines of triton-ascend).

## EG-2 — upstream td without `let constructor` ⇒ factory absent

Not a bug: create* functions are tblgen-generated (build tree, ADR-001). Documented in
pass-catalog. A `references` on python/src/passes.cc ADD_PASS wrappers is the runtime
composition point (see EG-3). Priority: none (informational).

## EG-3 — Python-side pipeline composition invisible

`python/src/passes.cc` ADD_PASS_WRAPPER bindings + Python compiler stages compose the
upstream Triton pipeline. Impact: upstream passes show no pipeline membership. Generic fix
direction: parse ADD_PASS_WRAPPER bindings as factory references and optionally follow
Python stage lists. Priority: High for Triton-ecosystem repos, Medium overall.

## EG-4 — bare generated-base inheritance (FIXED in Phase 8)

`class X : public XxxBase<T>` in headers (no `impl::`): RE_PASS_CLASS now accepts
`(impl::)?XxxBase<`. Re-validated on both repos (triton-to-linalg ownership chain resolved).

## EG-5 — gtest coverage not extracted

`third_party/ascend/unittest` (186 entities incl. tests) produces no TEST_COVERS_PASS
edges (C++ TEST() macros). Generic fix direction: gtest TEST(Suite, Name) discovery with
pass-arg matching in test bodies. Priority: Medium.

## Also fixed generically this phase

- factory suffix matching for dialect-prefixed td classes (createAccelerateMatmulPass ↔
  TritonGPUAccelerateMatmul) — kept, future-proofing for repos that do define factories.
