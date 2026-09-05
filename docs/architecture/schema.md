# Knowledge Graph Schema (Phase 0 contract)

Storage: SQLite (`.mlir-repomap/index.db`) + JSON metadata. Schema version field in
`meta` table; query API never exposes raw storage, so storage may change freely.

## Entities (`nodes` table)

| kind | id convention | extracted from |
|---|---|---|
| `dialect` | `dialect:<Name>` | `def X_Dialect : Dialect` in .td |
| `op` | `op:<Name>` (TableGen name, e.g. `HIVM_LoadOp`) | `def X : Op<Dialect, "name">` |
| `type` / `attr` | `type:<Name>` / `attr:<Name>` | `def X : TypeDef<..>` / `AttrDef<..>` |
| `pass` | `pass:<arg>` where arg = Pass ctor string arg (e.g. `hivm-fold`) or C++ `getArgument()` | Passes.td `def X : Pass<"arg">`, C++ pass classes |
| `pass_class` | `cppclass:<Name>` | C++ class deriving PassWrapper/OperationPass |
| `factory` | `func:<createXxxPass>` | `createXxxPass(` definitions in C++ |
| `pipeline` | `pipeline:<buildXxxPipeline|runXxx>` | `void buildXxxPipeline(OpPassManager&...)`, `runXxxCompile` |
| `pattern` | `pattern:<CppClass>` | `struct X : OpRewritePattern<FooOp>` etc. |
| `interface` | `interface:<Name>` | `def X : Interface<...>` in .td |
| `test` | `test:<repo-relative-path>` | files with `RUN:` lines |
| `symbol` | `func:<name>` / `cppclass:<Name>` | free C++ functions/classes of interest |
| `file` | `file:<relpath>` | git tracked files (lightweight; for provenance queries) |

Entity properties: `kind`, `name`, `summary` (one-line from td summary/remarks or docstring),
`file` (primary definition), `line`. Do not over-model: unknown repository concepts are added
as new kinds only when two+ target repos need them (ADR policy).

## Edges (`edges` table)

Directed; `src`/`dst` are node ids. Edge kinds (MVP set):

| kind | meaning | extractor | confidence |
|---|---|---|---|
| `DEFINES` | file defines entity | tablegen/cpppass | confirmed |
| `DIALECT_OWNS` | dialect -> op/type/attr | tablegen | confirmed |
| `PASS_HAS_FACTORY` | pass -> createXxxPass | name match td arg ↔ factory | confirmed/inferred |
| `PASS_IMPLEMENTS` | pass -> pass_class | getArgument() / PassWrapper in same file | confirmed |
| `PIPELINE_CONTAINS` | pipeline -> pass, ordered | `pm.addPass(...)` | confirmed |
| `PIPELINE_NESTS` | pipeline -> nested OpPassManager scope | `pm.nest<Op>()` | confirmed |
| `PIPELINE_CALLS` | pipeline -> pipeline | direct call of buildXxxPipeline | confirmed |
| `PRECEDES` | pass A before pass B in same pipeline scope | derived at extraction | confirmed |
| `CONDITION` | edge attribute (not node): guard expression on PIPELINE_* edges | `if (...) { addPass }` | confirmed |
| `PASS_USES_PATTERN` | pass/pipeline -> pattern | `patterns.add<X>(...)` within pass buildX or pass class | confirmed/inferred |
| `PATTERN_MATCHES_OP` | pattern -> op | template arg of OpRewritePattern/OpConversionPattern | confirmed |
| `PATTERN_CREATES_OP` | pattern -> op | `rewriter.create<BarOp>` in pattern body | confirmed (local), inferred via helpers |
| `TEST_COVERS_PASS` | test -> pass | pass arg / flag / pipeline name in RUN line | heuristic |
| `TEST_EXERCISES_PIPELINE` | test -> pipeline | pipeline builder/tool flag in RUN line | heuristic |
| `REFERENCES` | generic symbol reference fallback | text search | heuristic |

Conditional pipelines: `if (config.getX()) { pm.addPass(A); pm.addPass(B); }` produces
PIPELINE_CONTAINS edges with a `condition` property = the guard expression (outermost `if`
text captured with brace tracking). `#if/#ifdef` macro guards are recorded as
`condition_kind: "macro"`. Nesting scope is tracked with a scope stack (module-level vs
`nest<FuncOp>`), so the same pass can appear in multiple scopes with different order ids.

## Evidence model (`evidence` table)

```
edge_id -> file, line_start, line_end, snippet, extractor, confidence
```

A relation may have many evidence rows (e.g. pass defined in Passes.td AND registered in C++).
`confirmed` = direct source statement; `inferred` = reliable semantic derivation (e.g. name
matching td ↔ factory); `heuristic` = textual/name-based guess. Query results always expose
confidence and at least one evidence pointer.

## Incremental model

`meta` stores: repo root, indexed HEAD, branch, schema version, indexer version, per-file
content hashes (in `files` table), granularity dir mapping. Re-index: diff working tree vs
stored hashes → re-run extractors only on changed files; relations sourced from a changed file
are deleted before re-extraction (extractors are per-file pure functions over their file set;
pipeline files are cheap to re-run wholly). Diagnostics table records per-file failures.
