# Phase 7 Query Usage Audit

Per-pass query traces from the upgraded workflows (all runs start with `status`):

| pass | queries issued | new-query usage |
|---|---|---|
| hfusion-merge-vf | pass, pipeline bufferizationPipeline --brief, pipeline-builder, attribute RegisterTreeReductionSelectedAttr | pipeline-builder ✓, attribute ✓ |
| hfusion-flatten-ops | pass, pipeline ×2 --brief, pipeline-builder ×2, pattern-owner FlattenElemwiseOpPattern | pipeline-builder ✓, pattern-owner ✓ |
| hfusion-auto-vectorize-v2 | pass, pipeline --brief, pipeline-builder, attribute kRegisterTreeReduction* | all three ✓ |
| vf-fusion | pass, pipeline --brief, pipeline-builder, pattern-owner, attribute ×3 | all three ✓ |
| hivm-mark-stride-align | pass, tests, pipeline-builder alignStorage, attribute StrideAlignDimsAttr | all three ✓ |
| hivm-enable-stride-align | pass, tests, pipeline-builder alignStorage, attribute StrideAlignDimsAttr | all three ✓ |

Aggregate docs (repo-map step 6b) consumed the same queries via QueryService aggregation:
142 passes with chains → pattern-map.md; 86 attributes (43 with creators) → attribute-map.md.

Verdict: the Phase 6 query surface was sufficient — **no new query type was required**;
the upgrade was purely about workflow discipline plus two small engine fixes
(pattern-owner upward walk, k*Attr idiom capture).
