# Phase 7 Remaining Gaps

## RG-1 — Attribute creator side stays `inferred`

A class-body mention of `<Name>Attr::name` / `kXxxAttr` proves *involvement*, not
creation. The mark→enable→lowering chain reads correctly because producers also appear in
`createAlignMarkOp`-style call paths, but the graph cannot separate "creates" from
"reads/removes". Fix direction: trace marker-construction call sites
(`createAlignMarkOp`, `setAttr(...Attr::name...)`) as the creator evidence; needs an
op-attachment mini-extractor, not clangd. Priority: Medium (mislabels possible in
attribute-map for pure-consumer passes).

## RG-2 — BUILT_BY evidence snippet is a bare `{`

Cosmetic: the builder node carries the correct line, but the evidence snippet captured one
character. Fix: store the signature line in the builder evidence. Priority: Low.

## RG-3 — Feature tags are coarse keyword heuristics

`tests` feature tags (dynamic-shape/fusion/...) over-trigger (e.g. "merge" in a filename
tags fusion). Adequate for triage, not for coverage claims. Fix direction: anchor tags on
IR constructs (ops present in the test body) rather than substrings. Priority: Low-Medium.

## RG-4 — Populator chains stop at non-RewritePatternSet indirection

Builders that construct a pattern set internally (no `RewritePatternSet&` parameter)
break the chain. Unobserved in the six validated passes; revisit if a dossier hits it.

## RG-5 — Zero-pattern statements need workflow discipline

The "graph-confirmed zero patterns" claim is only as good as corpus scoping — passes whose
pattern registration lives outside the indexed corpus would be misreported. The repo-map
workflow's blind-spot section is the mitigation; keep it mandatory.
