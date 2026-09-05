# Goal: MLIR Pass Deep Analysis — {PASS_NAME}

You are working in the MLIR compiler repository at `{TARGET_REPO}`.

Before doing anything else, read and obey:
1. `{HARNESS}/adapters/deepseek-harness/conventions.md` — tool rules (RepoMap first, no repo-wide grep, evidence required).
2. `{HARNESS}/docs/workflows/pass-analysis.md` — the full 13-step method. Follow it in order; it is the source of truth. Do not redesign it.

Guardrails (do not skip, do not reinterpret):
- Start with `mlir-repomap --repo {TARGET_REPO} status` (index first if stale), then
  `mlir-repomap --repo {TARGET_REPO} pass {PASS_NAME}`. Resolve the name (arg / td class /
  factory / cpp class are all accepted); if ambiguous, ask, do not guess.
- Read ONLY the files named by the dossier's evidence pointers (expected ≤5 files).
  Repository-wide `grep`/`find`/`cat` in bulk is prohibited.
- Every claim in the dossier needs `file:line` evidence. "No discovered test" is the only
  coverage statement allowed without opening test files.
- Defect claims must follow the workflow's confidence ladder
  (Confirmed / Highly Likely / Potential) — complexity is not a bug.
- Do not modify the pass's source code. This is an analysis task.

Task: execute the `pass-analysis` workflow for pass `{PASS_NAME}`.

Output (exact path):
- `{TARGET_REPO}/docs/compiler-architecture/passes/{PASS_ARG}.md` (sections exactly as the
  workflow's output spec lists them), with the provenance header block.
- Register the dossier in `{TARGET_REPO}/docs/compiler-architecture/pass-catalog.md`.

Verification before finishing:
- [ ] All 13 spine steps are present (mark explicitly if a step yields "nothing found" and why).
- [ ] Pipeline context cites guards verbatim for every membership.
- [ ] Any suspected defect has: Problem / Evidence / Trigger / Impact / Confidence / Fix direction.
- [ ] A short run report lists: queries issued, files opened, tokens spent (approx), any
      missing query or blocked step.
