# Architecture Overview — MLIR Compiler Repository Analysis Harness

Status: Phase 0/1 baseline (living document; see decisions.md for changes from the original goal baseline).

## Purpose

A repository-first, evidence-first, MLIR-aware indexing and query system that helps a coding
agent (any agent: ZCode, DeepSeek Harness, Codex, Pi, Claude Code, ...) understand large
MLIR/LLVM compiler repositories: dialects, passes, pipelines, patterns, analyses, tests, and
cross-pass invariants — without grep-sweeping the repository.

Core principle: deterministic extraction produces the facts; the agent spends its tokens on
reasoning, not on repository discovery.

## Layer model

```
Layer A  repomap engine (this repo, repomap/)  — CLI-runnable core. No agent dependency.
Layer B  workflows (docs/workflows/*.md)       — agent-independent methodology, source of truth.
Layer C  adapters (adapters/)                  — thin protocol adapters: CLI is primary; MCP/ZCode
                                                 skills etc. are later phases and only wrap Layer A/B.
```

Hard boundaries:

- The engine must never import or depend on any agent product, skill system, or MCP SDK.
- Every agent-facing artifact (skill, prompt, MCP tool) is a thin adapter over the stable
  query contract; the contract lives in `docs/architecture/query-api.md`.
- Machine facts (`.mlir-repomap/` index, generated) are strictly separated from human
  knowledge (agent-reviewed `docs/compiler-architecture/` written by workflows).

## Engine internal structure

```
repomap/src/mlir_repomap/
├── index.py        # index build orchestration: extractors -> store; incremental invalidation
├── store.py        # persistence (SQLite) + metadata (HEAD, schema version, file hashes)
├── model.py        # entity/edge/evidence dataclasses + schema constants
├── query.py        # QueryService: the ONLY business logic for queries
├── cli.py          # thin argparse frontend over QueryService (must stay logic-free)
├── repo.py         # git facts: HEAD, branch, tracked/dirty files, change detection
├── extractors/
│   ├── tablegen.py # .td: Dialect / Pass / Op / Type / Attribute defs (structural, not full tblgen)
│   ├── cpppass.py  # C++ pass impls, createXxxPass factories, PassRegistration
│   ├── pipeline.py # addPass / addNestedPass / nest<> with ordering, nesting, conditions
│   ├── pattern.py  # OpRewritePattern<>/OpConversionPattern<>, patterns.add<>, rewriter.create<>
│   └── tests.py    # lit RUN lines, FileCheck, TEST_COVERS_PASS via pass/flag name matching
└── (semantic backend is an interface, not an MVP component; see decisions ADR-004)
```

Rules:

- **Fail soft**: a file that fails to parse records a diagnostic; indexing continues.
- **Deterministic before LLM**: all facts come from parsers/regex/git with source evidence.
- **Evidence model**: every relation carries ≥1 evidence (file, lines) plus a confidence
  (`confirmed` | `inferred` | `heuristic`). Multiple evidences per relation are allowed.
- **Fail-soft semantic backend**: no clangd/compile_commands required; when absent the engine
  degrades confidence, it never fails.

## Scope decisions (MVP)

Included: git facts, TableGen structural parsing, pass extraction (td-first), pipeline
extraction with conditions, pattern extraction, lit-test extraction, SQLite index, query CLI,
incremental re-index by file hash + directory granularity.

Excluded from MVP (see roadmap for phase assignment): MCP server, agent skills, clangd/LSP
integration, full TableGen compiler, full C++ call graph, ranking/PageRank, embeddings.

## Validation repository

AscendNPU-IR (BiShengIR) is the validation repository only. RegBase/HFusion/HIVM names must
never appear in the core engine; repo-specific knowledge lives in workflows and generated
human docs.
