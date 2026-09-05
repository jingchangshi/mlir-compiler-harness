# Generalization Report — Phase 8 verdict

## Do the relationships survive across Ascend compiler architectures?

**Yes, with two small generic fixes and one documented boundary.** The provenance graph
(pipeline identity, pattern ownership chains, attribute contracts, seq ordering) transferred
to a fundamentally different engineering pattern — a Python/C++ hybrid compiler — with:
- EG-4 fix: bare generated-base inheritance in headers (`XxxBase<T>` without `impl::`);
- factory suffix matching for dialect-prefixed td classes;
- and a consciously unimplemented boundary: **Python pipeline composition** (EG-1) —
  the authoritative `make_ttgir` stage list is invisible to the graph; audits read it
  alongside (pipeline-audit/make-ttgir.md documents the full chain by hand).

## Schema decision (goal §10)

No schema changes. The candidate concepts were judged:
- *Dialect-transition edge* (EG-2): both repos would benefit (triton→HIVM handoff;
  TTIR→TTGIR→LLVM chains) — but the information is already derivable from pass dossiers
  and op-ownership; promote to generic schema only when a second consumer workflow needs
  it. Deferred.
- *Python pipeline nodes*: belongs in the generic model if implemented (a Python stage
  list is morally a pipeline builder) — but per §10 it needs the EG-3/EG-1 design work
  first; recorded as the top next-phase candidate, not schema growth now.
- *Triton-specific concepts* (TTIR/TTGIR/TritonAscend): repository extension — they appear
  only in generated docs, never in the engine.

## New compiler idioms catalogued (goal §9)

1. EG-1 Python builds the C++ pipeline (`backend/compiler.py` stage lists +
   `ADD_PASS_WRAPPER` bindings) — needs a generic "Python pipeline builder" abstraction.
2. EG-2 dialect-transition edges — deferred (see above).
3. EG-3 registration idioms: bare generated-base in headers (FIXED), C++-only
   PassRegistration families, upstream no-constructor td, hardcoded kernel-name carve-outs
   in pass logic (`pcb10_tc01_kernel` — reported to owners via dossier).

## Ecosystem verdict

The harness now covers the Ascend stack end-to-end: triton-ascend (frontend → TTIR/TTGIR
→ three lowering frontiers) and AscendNPU-IR (Linalg → HIVM → hardware). Senior-engineer
first-pass understanding is achieved on both: identity, position, contracts, and
provenance are queries; Python stage lists are the single remaining manual read.
