# Architecture Validation — repo-map + extractor coverage

## repo-map execution (goal §3)

All six architecture docs generated unmodified for triton-ascend
(`docs/compiler-architecture/triton-ascend/`): repository-map, dialect-map, pipeline-map,
pass-catalog, pattern-map (142 passes with chains / 190 confirmed-zero), attribute-map
(29 entities). Evidence spot-checks performed during dossier writing (td defs, pass
classes, builder bodies).

## Extractor coverage per goal §4-6

- Dialect/Operation: 8 dialects; **mixed modes confirmed** — upstream direct
  `Op<Triton_Dialect,...>` defs (Triton 50 ops) vs Ascend multiclass aliases
  (TritonAscend 16 ops); cross-file ownership resolves both styles.
- Pass registration: three idioms in one repo — td+`let constructor` (Ascend), td
  without constructor (upstream; factory correctly absent per ADR-001), C++
  `PassRegistration` (ComputeBlockOpt family). All produce correct pass entities.
- Pipeline builders: C++ builders + `runOnOperation`-internal builders (mislabel EG-3/
  renamed) + **Python stage lists** (EG-1) — see pipeline-audit/make-ttgir.md.
- Pattern provenance: populate* chains and direct adds resolve; ownership chain for
  `triton-to-linalg` confirmed after the EG-4 fix (bare generated-base inheritance).
- Attribute provenance: `*Attr::name` + `k*Attr` idioms captured (29 entities).

## Workflow verdict

The repo-map and pass-analysis workflows ran without modification; the only manual step
was reading `backend/compiler.py` stage lists for the Python pipeline (EG-1 gap).
