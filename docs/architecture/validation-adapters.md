# Validation Report — Agent Adapters (Phase 4)

Date: 2026-09-05 · Target repo: AscendNPU-IR (HEAD `5671889a3`) · Harness @ `d3fb667` + Phase 4 engine fixes.

## What was validated

### DeepSeek Harness style (`pass-analysis-goal.md`), input: "分析 FlattenOps Pass"

Simulated a capability-limited agent following ONLY the goal template + conventions +
workflow file, with the template's fixed query steps and file budget:

1. `status` → stale detected → (conventions) refresh first. 0.4 s incremental, 0 re-extract.
2. `pass FlattenOps` → **initially `not found`** (engine only matched pass args).
   Engine fixed in-response: multi-strategy resolution (arg / td class / cpp class /
   factory) with explicit ambiguity. Re-run: `FlattenOps` → **ambiguous**
   `{hfusion-flatten-ops, hivm-flatten-ops}` (both dialects have a `FlattenOpsPass` /
   `createFlattenOpsPass`) — template rule "if ambiguous, ask, do not guess" is now backed
   by the tool; the run documents choosing `hivm-flatten-ops`. `HIVMFlattenOps` resolves
   directly.
3. `pipeline hivmPostBufferizationOptimizationPipeline --brief` → 79 stages, flatten at
   orders 16/17 in `func::FuncOp` scope (brief mode added during validation: full output
   was 41 KB / ~10k tokens, brief is 15 KB / ~3.8k tokens — within budget).
4. `tests hivm-flatten-ops` → 1 test (flag-confirmed).
5. Evidence read: 2 targeted regions of `FlattenOps.cpp` (skip-logic 53-81, driver 121-135).

Fresh dossier generated (`/tmp/fresh-hivm-flatten-ops.md` during validation) and compared
against the Phase 3 dossier on 9 key facts (pipeline, orders, pred/succ, decomposePhase
coupling, left-padding skip, subview exception, 224xf32 example, both potential issues):
**9/9 identical — zero methodology drift.** Total query output ≈ 4.9k tokens; source bytes
read ≈ 60 lines. The "repository discovery by tool, tokens on reasoning" boundary held.

### ZCode style (3 skills)

- Frontmatter (`name`, single-line `description`) valid for all three skills.
- Trigger boundaries: each description explicitly excludes the other two workflows
  ("Not for …") — no overlap found for the three task archetypes.
- Harness resolution: `$MLIR_COMPILER_HARNESS` unset → sibling fallback
  (`../mlir-compiler-harness/docs/workflows/...`) works from the target repo.
- No-rescan rule: skill entry is `status` → conditional `index`; incremental refresh on an
  unchanged tree costs 0.4 s / 0 re-extracts (verified).
- Result consistency: the skill's fixed query strategy is the same one validated above
  (same queries, same evidence pointers) → same dossier.

## Problems found & fixed during validation

1. **Query API gap — pass name resolution** (blocked step 2): `pass <name>` accepted only
   the pass argument. Fixed generically: case-insensitive arg, td class, cpp class, and
   factory-name resolution; multiple candidates return `{"error":"ambiguous","candidates":[...]}`
   instead of a silent pick (query-api.md updated; 3 regression tests added, 10/10 pass).
2. **Query API gap — pipeline output size** (budget breach): full stage list with evidence
   snippets was ~41 KB for a 79-stage pipeline. Added `pipeline <name> --brief`
   (no evidence rows; evidence remains available per-stage via `evidence` command).
3. Adapter layering held: both fixes are engine/contract changes behind the same CLI;
   no template or skill needed rewording.

## Known adapter limitations (accepted)

- Templates hardcode the output root `docs/compiler-architecture/`; a target repo with a
  different convention needs the placeholder edited (documented, not parameterized).
- Skill trigger wording is English-only; Chinese requests ("分析 FlattenOps Pass") rely on
  the agent's language matching, which worked in simulation.
- `MLIR_COMPILER_HARNESS` must be exported in the agent's environment; the sibling-path
  fallback covers the common checkout layout only.

## Architecture implications

ADR-010 records the adapter contract validated here. Next-phase candidates were re-ranked
(see roadmap): adapter hardening through real multi-agent use beats MCP (no hot-path
pressure observed yet) and clangd (no wrong-fact incident in either validation run).
