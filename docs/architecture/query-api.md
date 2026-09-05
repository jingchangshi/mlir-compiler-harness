# Stable Query Contract v1

All agent-facing layers (CLI, future MCP, Python API, workflow docs) depend ONLY on this
contract. `QueryService` (query.py) is the single implementation; CLI and MCP are frontends.

JSON envelope for every command:

```json
{ "command": "...", "args": {...}, "index": {"head": "...", "branch": "...", "indexed_at": "...",
  "schema_version": 1, "stale": true, "dirty_files": 3}, "result": {...} }
```

`stale` = current HEAD or working tree differs from indexed snapshot (client decides whether
to re-index; workflows must refresh before reasoning if stale).

## Commands

| CLI | service method | returns |
|---|---|---|
| `status` | repo_status() | repo root, HEAD, branch, dirty/changed vs index, counts by entity kind, diagnostics |
| `modules [--depth N]` | modules(depth=2) | directory modules (top N path levels, default 2) with entity counts |
| `dialects` | dialects(name=None) | dialect list w/ ops/types/attrs counts, def file |
| `passes` | passes(query=None) | pass list: arg, kind (td/cpp), def file, summary |
| `pass <name>` | get_pass(name) | full dossier (below) |
| `pipelines` | pipelines() | pipeline list w/ entry file, pass count |
| `pipeline <name>` | get_pipeline(name) | ordered stages incl. conditions, nested scopes, called sub-pipelines |
| `symbol <name>` | find_symbol(name) | matching entities (class/function/op/pattern) + def evidence |
| `references <name>` | get_references(name) | edges/mentions of the entity grouped by kind |
| `tests <pass-or-pipeline>` | get_tests(name) | covering tests w/ RUN lines + confidence |
| `changed [base]` | get_changes(base=None) | files changed vs index (and vs base ref if given) + impacted entities |
| `evidence <node-or-edge-id>` | get_evidence(id) | all evidence rows with file:line + snippet |

Token discipline: every command returns compact JSON with `file:line` pointers, never file
contents; the agent opens only what it needs. `pass <name>` is the one-stop dossier for the
pass-analysis workflow.

## `pass <name>` dossier (contract)

```json
{ "pass": {"id","arg","summary","file","line"},
  "definition": [...],           // td def / cpp class
  "declaration": [...],          // headers
  "factory": [...],              // createXxxPass
  "registration": [...],         // PassRegistration / generated registration
  "pipeline_memberships": [ {"pipeline","scope","order","condition","confidence"} ],
  "predecessor"/"successor": per membership,
  "patterns": [ {"pattern","matches_ops","creates_ops"} ],
  "analyses": [],                // MVP: text-based, usually empty; interface reserved
  "symbols": [], "files": [],
  "tests": [...], "diagnostics": [] }
```

Unresolved sections return empty lists, never nulls or errors — partial answers are valid.
