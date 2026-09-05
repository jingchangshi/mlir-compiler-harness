# Goal: Pipeline Audit — {PIPELINE_NAME}

You are working in the MLIR compiler repository at `{TARGET_REPO}`.

Before doing anything else, read and obey:
1. `{HARNESS}/adapters/deepseek-harness/conventions.md` — tool rules (RepoMap first, no repo-wide grep, evidence required).
2. `{HARNESS}/docs/workflows/pipeline-audit.md` — the audit-lens method. Follow it; it is the source of truth. Do not redesign it.

Guardrails (do not skip, do not reinterpret):
- Start with `mlir-repomap --repo {TARGET_REPO} pipeline {PIPELINE_NAME}`; then `tests` and
  `changed` per the workflow. Read only the pipeline-builder regions the evidence names.
- Do not re-summarize each pass individually (that is `pass-analysis.md`, not this workflow).
- Audit lenses must each end in either a finding or an explicit "checked, OK".
- Guard mutual exclusion must be verified from the guard text you can see; if helpers hide
  it, say so and mark the finding Potential.
- RepoMap reporting "no discovered test" is the only coverage fact the tools give; human
  conclusions about coverage semantics must be labeled as reasoning, not as tool output.
- Do not modify pipeline source code. This is an audit task.

Task: execute the `pipeline-audit` workflow for pipeline `{PIPELINE_NAME}`.

Output (exact path):
- `{TARGET_REPO}/docs/compiler-architecture/pipelines/{PIPELINE_NAME}.md` with sections:
  `# Pipeline Overview` · `# Findings` (numbered, classified: Problem / Evidence / Trigger /
  Impact / Confidence / Fix direction) · `# Invariant Map` · `# Coverage` · `# Recommendations`.
- Register the audit in `{TARGET_REPO}/docs/compiler-architecture/pipeline-map.md`.

Verification before finishing:
- [ ] All 8 lenses addressed (finding or "checked, OK").
- [ ] The stage flow in the Overview matches the query output including conditions verbatim.
- [ ] A short run report lists: queries issued, files opened, any query that was missing.
