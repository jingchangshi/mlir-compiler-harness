# Review Memory Gap — "what did we already learn about this pass?"

Phase 17 design document (Step 1). Status quo reproduced at commit `47e5ccf`
(Phase 16), indexer v46.

## What an agent must do today to "remember" a pass

Before analyzing a pass, the current loop forces the agent to re-assemble memory
from four separate surfaces, each with its own invocation and conventions:

```
source re-read        mlir-repomap pass <name> + evidence-pointed files
findings              mlir-repomap findings list --pass-name …
history               mlir-repomap findings check / finding-impact <id> per finding
review record         re-open docs/compiler-architecture/passes/<dossier>.md and
                      scroll to the Compiler Review section (if one exists)
```

Nothing answers the memory questions directly:

| question | today |
|---|---|
| What was previously reviewed? | manually locate the dossier, find the review section |
| Which invariants were protected? | re-read the record bullets; separately run pass-constraints |
| Which evidence supports them? | chase `file:line` pointers by hand across record, findings, graph |
| What changed since last review? | run finding-impact per finding, with the right baseline |

## The three cases that motivate the query

**AV2-001** (`pass:hfusion-auto-vectorize-v2`). The memory exists, scattered: the
Phase 13 review record (dossier `auto-vectorize-v2.md`) states the verifier-
completeness invariant; the finding's regression memory records the fallback crash
fix (7875b76ea) and the fallback removal (fa682a1a3); Phase 16 proved the guard
`failed(result` @ :1406 was *added* with the fallback removal. Reconstructing that
takes five queries plus two file reads. A new agent skipping any one of them loses
the invariant or its history.

**MVS-001** (`pass:hfusion-merge-vf`). The review record names the UNGUARDED
single-use assumption; the graph holds the two verify guards (:1422/:1625); the
finding records the A5-migration provenance (4ddead06f). Again: one memory, four
surfaces, zero queries that join them.

**TTL-001** (`pass:triton-to-linalg`, single-repo scope). The review record's
flatten contract, the finding's dual-repo evidence pointers, and the Phase 15
attribute provenance (`attribute:StrideAlignDimsAttr`) are all needed before any
re-review; today only by manual re-assembly.

## Design consequence (Steps 2–3)

1. **`review <pass>`** — one deterministic lookup joining: graph pass identity, the
   dossier's Compiler Review record (extracted verbatim — quoted, never
   regenerated), findings linked by pass field or `entity_refs`, deterministic
   constraint records (the graph-side invariant guards), and per-finding recent
   impact signals (Phase 16 machinery, each finding's own baseline or `--since`).
   No reasoning is generated anywhere in the output.
2. **Evidence catalog** — `evidence <entity>` grows from raw evidence rows to
   evidence points: the entity, its evidence rows, **referenced-by findings**
   (matched by evidence `ref`/file and `entity_refs`), and **recent history**
   (commits touching the entity's file). Structural matching only — no embedding,
   no semantic similarity, anywhere.
