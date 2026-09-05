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
| `findings list [--status S] [--pass-name P] [--category C] [--has-regression] [--dir D]` | FindingService.list | validated finding inventory (doc-layer artifacts, ADR-020): id, category, pass, status, created_at, statement, evidence files; invalid documents surface in `diagnostics`, never abort the listing |
| `findings check [--since REF] [--dir D] [--git-repo R] [--format text\|json]` | FindingService.check | git-aware drift report over finding evidence: commits touching each evidence file since the finding's baseline (review.baseline_commit or --since), snippet-presence verification ("evidence changed"), and a `needs_review` verdict per finding in the goal format ("Finding <id> / possibly affected by commit … / Needs review"). Never mutates finding status; external-repo evidence (a `repo:` field) is noted, not drift-checked |
| `findings show <id>` | FindingService.show | full finding record including history and regression memory |

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

## Finding artifacts (doc layer, ADR-020)

Findings are agent-written YAML documents (`<ID>.yaml`) in a target repo's
`docs/compiler-architecture/findings/` directory (triton-ascend findings live in the
harness repo, mirroring the Phase 8 doc placement). They are **not** graph entities —
the `findings` command family reads them directly and validates against this contract:

```yaml
finding:
  id: AV2-001                  # unique, short pass-derived prefix + number
  category: correctness        # correctness | coverage | performance | architecture | opportunity
  pass: auto-vectorize-v2      # pass arg (or pipeline identity) the finding is about
  statement: >-                # one-paragraph claim
  evidence:                    # non-empty; what the claim rests on
    - file: <repo-relative path>
      lines: N | N-M           # optional
      kind: constraint|code|code-comment|test|pipeline   # optional
      ref: <graph node id>     # optional; links to a deterministic fact
      repo: <other-repo>       # optional; cross-repo evidence (not drift-checked)
      snippet: "<exact text>"  # optional; enables drift verification
  reasoning: >-                # agent reasoning (layer 2), labeled as such
  status: open                 # open | acknowledged | in-progress | resolved | rejected | superseded
  created_at: YYYY-MM-DD
  created_by: <phase/session>  # optional
  source: <dossier anchor>     # optional
  superseded_by: <id>          # required iff status: superseded
  history:                     # append-only lifecycle log; every entry needs at + reason
    - status: acknowledged
      at: YYYY-MM-DD
      reason: <why>            # mandatory — a transition without a reason is invalid
      evidence: [...]          # at least one of evidence / reference is mandatory
      reference: <doc/commit/URL>
  regression:                  # optional — Compiler Regression Memory
    historical_concern: >-
    resolved_commit: <sha>     # optional
    regression_risk: low|medium|high
  review:
    baseline_commit: <sha>     # target-repo HEAD when the finding was created/last reviewed
```

Lifecycle rules enforced by `validate_finding`: transitions are recorded in `history`
(never overwriting earlier entries); `resolved`/`rejected`/`superseded` require a
matching history entry; `superseded` requires `superseded_by`. The engine never
advances a status itself — `findings check` only reports drift and "Needs review".
