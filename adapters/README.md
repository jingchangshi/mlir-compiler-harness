# Adapters

Thin per-agent integration layers. The engine (`repomap/`) and the workflows
(`docs/workflows/`, Phase 3) are the source of truth; adapters only translate.

- `zcode/` — skills/commands (Phase 4, not yet implemented).
- `deepseek-harness/` — goal/system prompt templates + CLI conventions (Phase 4).
- MCP server — Phase 5, a 1:1 wrapper over `mlir_repomap.query.QueryService`.

Adapter contract: an agent is supported if it can (a) run `mlir-repomap` in a shell, or
(b) speak MCP. Nothing else is required; no adapter may modify the engine.
