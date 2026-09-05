# Goal: Repository Architecture Mapping

You are working in the MLIR compiler repository at `{TARGET_REPO}`.

Before doing anything else, read and obey:
1. `{HARNESS}/adapters/deepseek-harness/conventions.md` — tool rules (RepoMap first, no repo-wide grep, evidence required).
2. `{HARNESS}/docs/workflows/repo-map.md` — the full method. Follow it exactly; it is the source of truth. Do not redesign it.

Guardrails (do not skip, do not reinterpret):
- First run `mlir-repomap --repo {TARGET_REPO} status`; if `stale: true`, run `mlir-repomap --repo {TARGET_REPO} index`.
- Every fact in your output must come from a RepoMap query result or a source file opened at a `file:line` pointer from such a result.
- Do not infer relationships from file or pass names. Unverified relationships stay unreported.
- Do not read source files in bulk; the workflow names the only files you may open (evidence spot-checks).
- Do not run the other workflows (no per-pass analysis, no pipeline audit).

Task: execute the `repo-map` workflow to build/refresh the human architecture layer.

Output (exact paths, created if missing):
- `{TARGET_REPO}/docs/compiler-architecture/README.md`
- `{TARGET_REPO}/docs/compiler-architecture/repository-map.md`
- `{TARGET_REPO}/docs/compiler-architecture/dialect-map.md`
- `{TARGET_REPO}/docs/compiler-architecture/pipeline-map.md`
- `{TARGET_REPO}/docs/compiler-architecture/pass-catalog.md`

Verification before finishing:
- [ ] `status`, `modules`, `dialects`, `pipelines`, `passes` queries all appear in the run (cite the numbers you used).
- [ ] At least 3 evidence spot-checks were performed by opening source at query-given `file:line` (one dialect def, one pipeline builder, one pass def) and their results are stated in the docs.
- [ ] Every doc carries the provenance block (HEAD, indexer version, date, counts).
- [ ] A short run report lists: queries issued, files opened, any query that was missing/insufficient.
