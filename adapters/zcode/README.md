# ZCode Adapter

Three thin skills that run the agent-independent workflows inside ZCode. Installed into a
skill directory (e.g. `~/.zcode/skills/<name>/SKILL.md` or a plugin), they trigger on
architecture-mapping / pass-analysis / pipeline-audit requests respectively.

## Layout

```
skills/
├── mlir-repo-map/SKILL.md          → docs/workflows/repo-map.md
├── mlir-pass-analysis/SKILL.md     → docs/workflows/pass-analysis.md
└── mlir-pipeline-audit/SKILL.md    → docs/workflows/pipeline-audit.md
```

## Install

```bash
export MLIR_COMPILER_HARNESS=/absolute/path/to/mlir-compiler-harness
cp -r adapters/zcode/skills/* ~/.zcode/skills/
```

The skills resolve the harness at run time via `MLIR_COMPILER_HARNESS` (fallback:
`<target-repo>/../mlir-compiler-harness`) and read the workflow files from there — the
skills intentionally stay methodology-free (thin-adapter rule, ADR-010). The env var must be
exported in the environment ZCode runs in.

## Trigger boundaries (disambiguation)

- repo-level "understand/map/document the compiler repo" → `mlir-repo-map`
- a named pass → `mlir-pass-analysis`
- a named pipeline / cross-pass review → `mlir-pipeline-audit`

The descriptions above encode these boundaries; keep them distinct when editing.
