# Workflow: Repository Architecture Mapping (`repo-map`)

Agent-independent methodology. Any agent that can run `mlir-repomap` in a shell can execute
this workflow verbatim. This file is the source of truth; agent-specific skills/prompts are
thin wrappers around it.

## When to run

- First contact with a compiler repository;
- The repository changed substantially (`mlir-repomap status` reports `stale: true` after a
  big diff, or `docs/compiler-architecture/` is missing/stale);
- The human architecture knowledge must be (re)generated.

Scope guard: this workflow maps architecture. It does NOT do per-pass correctness review
(that is `pass-analysis.md`) nor cross-pass auditing (`pipeline-audit.md`).

## Inputs / Outputs

- Input: repository root with an initialized RepoMap index (`.mlir-repomap/`).
- Output: `docs/compiler-architecture/` in the target repository:
  `README.md`, `repository-map.md`, `dialect-map.md`, `pipeline-map.md`, `pass-catalog.md`,
  `pattern-map.md`, `attribute-map.md` (provenance maps, Phase 7).

## Procedure

1. **Status & freshness**
   `mlir-repomap status`. If `index.stale` is true → `mlir-repomap index` (incremental).
   Record HEAD, branch, entity counts, diagnostics. If diagnostics > 0, note which files
   failed to parse (those areas are blind spots in everything below).

2. **Modules** — `mlir-repomap modules`. Identify the major areas of the codebase by entity
   density. Do not invent module boundaries from file names alone.

3. **Dialects** — `mlir-repomap dialects`. For each dialect record: name, definition file,
   owned ops/types/attrs counts. Flag dialects with 0 owned entities for manual inspection
   (often the ops live in a differently-named .td).

4. **Pipelines** — `mlir-repomap pipelines`, then `mlir-repomap pipeline <name>` for the
   top-level entry pipelines (highest stage counts and any name containing compile/opt).
   For each: entry file, sub-pipeline calls, conditional stages (guards) — keep guard text
   verbatim in the output doc.

5. **Passes** — `mlir-repomap passes`. Do not paste the catalog; summarize by dialect/directory
   and list passes that appear in ≥1 pipeline. Passes in no pipeline are likely
   opt-tool-only (`bishengir-opt`-style) — group them as "tool-invocable, not pipelined".

6. **Evidence spot-check (mandatory)** — open the source at the evidence pointers for at least:
   one dialect def, one top-level pipeline (verify 2–3 addPass lines), one pass def.
   If evidence contradicts the graph, treat it as an engine bug: record it in the output
   document's "Provenance & caveats" section and file an issue in the harness repo — do not
   silently fix the doc by hand.

6b. **Provenance maps** — aggregate the graph's provenance layer:
   - `pattern-map.md`: for each pass with registered patterns, the ownership chain
     (pass → populator function → pattern), with confidence and the `disambiguation`
     flags where locality heuristics were applied; passes confirmed to register no
     patterns are listed as such.
   - `attribute-map.md`: for each `attribute:<Name>` entity, producers (confirmed
     creators) and consumers (referencing files/passes) — the cross-pass attribute
     contract inventory.
   Both maps are generated from RepoMap queries (CLI or QueryService); hand-edits follow
   the `<!-- human-note -->` rule below.

7. **Generate human docs** into `docs/compiler-architecture/`:
   - `README.md` — how this dir was produced (workflow, HEAD, index version, date) and how to refresh;
   - `repository-map.md` — modules, corpus scope, build entry points, key directories;
   - `dialect-map.md` — table of dialects + owned entities + notes from spot-checks;
   - `pipeline-map.md` — top-level pipelines, their stage flow with conditions, sub-pipeline graph;
   - `pass-catalog.md` — summarized catalog + index into `passes/<Pass>.md` dossiers (produced
     by `pass-analysis.md`).

## Output rules

- Every non-trivial claim carries `file:line` evidence taken from query results.
- Mark items whose evidence is `heuristic` explicitly (e.g. test links).
- Machine facts live in `.mlir-repomap/`; these docs are the human-reviewed layer. If a human
  edits them, add a `<!-- human-note -->` so regeneration does not silently overwrite intent.
- Regeneration is cheap and idempotent; never hand-maintain machine-derivable lists.
