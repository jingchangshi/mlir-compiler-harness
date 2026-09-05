# Phase 5 Validation — ZCode-driven Deep Compiler Analysis on AscendNPU-IR

Scope per goal: ZCode only × AscendNPU-IR only; all analyses executed through the ZCode
adapter path (`adapters/zcode/skills/*` → `docs/workflows/*` → `mlir-repomap` CLI →
evidence-pointed source reads). No engine changes were made during analysis; findings are
recorded in `query-gaps.md` / `workflow-gaps.md`.

Layout:

```
pass-analysis/    per-pass validation records (query trace + quality assessment);
                  full dossiers live in the target repo:
                  AscendNPU-IR/docs/compiler-architecture/passes/<name>.md
pipeline-audit/regbase.md
query-gaps.md     RepoMap capability gaps found during analysis
workflow-gaps.md  workflow methodology gaps found during analysis
```

Runs: 2026-09-05, HEAD `5671889a3`, harness @ Phase 4 (`c6ebc56`), indexer v9,
0 parse diagnostics.

Summary of the three goal questions:

1. **Can ZCode complete real analysis via the skills?** Yes — all 6 pass dossiers + the
   regbase audit were produced end-to-end through the skill conventions; only the
   evidence-pointed source files were read; no repo-wide grep was needed.
2. **Is the Query API sufficient?** Sufficient for identity/position/structure; gaps remain
   for pattern ownership (free-function populate), attribute-level producer/consumer,
   feature-level test metadata, and cross-scope execution order (see query-gaps.md).
3. **What actually blocks compiler reasoning?** Nothing hard-blocked; the recurring
   friction was QG-3 (pattern↔pass ownership missing in all 6 analyses) and the manual
   attribute-consumer search (QG-4). Both are engine-level, both have clear fix designs.
