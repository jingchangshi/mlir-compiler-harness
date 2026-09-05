# Knowledge Graph Schema (Phase 0 contract)

Storage: SQLite (`.mlir-repomap/index.db`) + JSON metadata.

Pipeline identity (ADR-012): node id is `pipeline:<file>:<name>` — same-name builders in
different files never merge (AscendNPU-IR's dual `alignStoragePipeline` is the validated
case). Queries by bare name return the unique match or an explicit ambiguity error with
file-qualified candidates. `PIPELINE_CONTAINS` edges carry both `order` (per-scope) and
`seq` (monotonic source order across scopes, QG-6). Schema version field in
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
| `test` | `test:<repo-relative-path>` | files with `RUN:` lines; `summary` carries heuristic `features:` tags (dynamic-shape, reduction, fusion, vectorization, bufferization, stride-align, nested-region) |
| `function` | `function:<file>:<name>` | C++ functions that take `RewritePatternSet&` (pattern-set helpers/populators), pipeline builders, and **Python pipeline-composition functions** (signature-based: pass-manager param/usage, never name-based) |
| `binding` | `binding:<name>` | PyBind-style binding boundary: a string name mapped to a C++ function/factory via `m.def("name", fn)` or wrapper macros; lambda bodies are brace-matched to find the mapped factory |
| `attribute` | `attribute:<Name>` | IR attribute names referenced as `<Name>Attr::name` |
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
| `PASS_USES_PATTERN_POPULATOR` | pass -> pattern-set function | call site of a `RewritePatternSet&`-taking function from a pass class/method | confirmed (ADR-012) |
| `FUNCTION_DEFINES_PATTERN` | function -> pattern | `patterns.add<X>(...)` inside a pattern-set function | confirmed |
| `FUNCTION_CALLS` | function -> function | pattern-set helper call chain (populate -> register -> add) | confirmed |
| `PIPELINE_BUILT_BY` | pipeline -> builder function | pipeline builder definition | confirmed (ADR-012) |
| `BINDING_MAPS_TO` | binding -> C++ function/factory | PyBind def / wrapper macro / lambda body factory call | confirmed (ADR-015) |
| `PYTHON_COMPOSES` | Python composition function -> binding | `passes.<group>.add_*(pm, ...)` stage call inside a composition function | confirmed |
| `BINDING_EXPOSES_PASS` | binding -> pass | resolved chain binding -> factory -> pass | confirmed (ADR-015) |
| `CREATES_ATTRIBUTE` | pass -> attribute | `<Name>Attr::name` referenced inside pass class body | inferred |
| `REFERENCES` | generic symbol reference fallback | text search | heuristic |
| `PATTERN_MATCHES_OP` | pattern -> op | template arg of OpRewritePattern/OpConversionPattern | confirmed |
| `PATTERN_CREATES_OP` | pattern -> op | `rewriter.create<BarOp>` in pattern body | confirmed (local), inferred via helpers |
| `TEST_COVERS_PASS` | test -> pass | pass arg / flag / pipeline name in RUN line | heuristic |
| `TEST_EXERCISES_PIPELINE` | test -> pipeline | pipeline builder/tool flag in RUN line | heuristic |
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
