# DeepSeek Harness conventions — RepoMap usage

These rules are referenced by every goal template. They exist because the harness may run
with models of varying capability: repository discovery must be done by deterministic tools,
and the model's budget must go to compiler reasoning.

## Tool resolution

- `mlir-repomap` CLI (preferred): `mlir-repomap --repo <target-repo> <command> [args]`.
- Python API fallback (only if the CLI is missing): `from mlir_repomap.query import QueryService`.
- Workflow resolution: `MLIR_COMPILER_HARNESS` (absolute path to the harness checkout).
  If unset, try `<target-repo>/../mlir-compiler-harness`. If still missing, abort and ask the
  user; never substitute guessed methodology.

## Mandatory behavior

1. **Read the workflow first.** The referenced `docs/workflows/<workflow>.md` file is the
   method. Do not redesign, abbreviate, or extend it.
2. **RepoMap before source.** Every analysis starts from `mlir-repomap` queries; source files
   are opened only at `file:line` pointers returned by queries.
3. **No repository-wide grep/find** unless a workflow step literally cannot proceed; if that
   happens, stop that step, write what query would have answered it, and continue.
4. **No name-based guessing.** A relation not backed by a query result + evidence pointer is
   marked `heuristic` or omitted.
5. **Evidence on every load-bearing claim** — `file:line` citations in the output document.
6. **Fail soft.** One failed query or unreadable file is recorded and the run continues.
7. **Write results to the exact output path the workflow specifies** and register the new
   document in the index file it names (e.g. `pass-catalog.md`).
8. **Refresh before reasoning**: if `mlir-repomap status` reports `stale: true`, run
   `mlir-repomap index` first.

## Budget guardrails (from harness validation, AscendNPU-IR)

A pass analysis is expected to cost: 1 `status` + 1 `pass` + 1–3 `pipeline`/`tests` queries
(each ≤ ~1.5k tokens of output) + reading ≤5 source files. Significantly exceeding this is a
harness/tooling defect: record it in the run report instead of pushing through.
