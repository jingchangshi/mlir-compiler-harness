# mlir-compiler-harness

Agent-independent analysis harness for large MLIR/LLVM compiler repositories
(Agent/Harness-agnostic: ZCode, DeepSeek Harness, Codex, Pi, ... — via CLI today; MCP/Skills
are thin adapters, never the core).

- `docs/architecture/` — living architecture: overview, schema, query API, decisions (ADRs),
  status, roadmap, validation report.
- `repomap/` — the engine (Python, stdlib only): `pip install -e repomap/` gives `mlir-repomap`.

```bash
cd <mlir-repo> && mlir-repomap index            # full/incremental index into .mlir-repomap/
mlir-repomap status                             # index state, entity counts
mlir-repomap pass hivm-flatten-ops              # one-stop pass dossier
mlir-repomap pipeline buildHFusionRegBasePipeline
mlir-repomap dialects / passes / tests / changed / evidence ...
```

Machine facts live in `<repo>/.mlir-repomap/` (gitignored); human knowledge produced by
workflows goes to `<repo>/docs/compiler-architecture/`.
