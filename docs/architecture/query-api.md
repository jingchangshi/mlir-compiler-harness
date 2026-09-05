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
| `pass <name>` | get_pass(name) | full dossier (below). `<name>` may be the pass arg, td class, cpp class, or factory name; case-insensitive. Multiple candidates return `{"error":"ambiguous","candidates":[...]}` — callers must ask, never guess |
| `pipelines` | pipelines() | pipeline list w/ entry file, pass count |
| `pipeline <name> [--brief]` | get_pipeline(name, brief) | ordered stages incl. conditions, nested scopes, called sub-pipelines. `--brief` omits per-stage evidence rows (stage-level evidence remains available via the `evidence` command) |
| `symbol <name>` | find_symbol(name) | matching entities (class/function/op/pattern) + def evidence |
| `references <name>` | get_references(name) | edges/mentions of the entity grouped by kind |
| `tests <pass-or-pipeline>` | get_tests(name) | covering tests w/ RUN lines + confidence |
| `changed [base]` | get_changes(base=None) | files changed vs index (and vs base ref if given) + impacted entities |
| `evidence <node-or-edge-id>` | get_evidence(id) | all evidence rows with file:line + snippet |
| `pattern-owner <pattern>` | pattern_owner(name) | provenance chain: pattern -> defining pattern-set function(s) -> pass(es), with evidence |
| `pipeline-builder <pipeline>` | pipeline_builder(name) | file-qualified builder function(s), sub-pipeline calls, callers |
| `attribute <name>` | get_attribute(name) | attribute provenance: referencing files (heuristic) + confirmed creating pass classes |
| `pipeline-composition <pass>` | pipeline_composition(name) | cross-language construction chain: Python composition function → binding → C++ factory → pass, with evidence |
| `ecosystem --repos A --repos B <status\|handoff\|boundary\|contract> [name]` | EcosystemQueryService | cross-repository handoff graph: dialect/op/attribute handoffs between repo indexes, per-repo boundary view, shared attribute contracts (ADR-017) |
| `pass-intent <pass>` | pass_intent(name) | layered compiler intent: graph facts only (stated intent, deterministic label with confidence, boundary evidence, constraint counts) — agent interpretation stays in dossiers (ADR-018) |
| `pass-constraints <pass>` | pass_constraints(name) | deterministic constraint records: kind (legality-guard/match-failure/early-return/pass-failure/todo), condition text, evidence line |

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
