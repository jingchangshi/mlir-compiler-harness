"""Lit/FileCheck + gtest test extractor.

lit: RUN-line flag matching (TEST_COVERS_PASS); at resolve time the link is
     upgraded to `exact` when the flag is a confirmed pass arg.
gtest (Phase 16, EG-5 stage 1): TEST()/TEST_F() files become test nodes; pass
     links are derived at resolve time by normalized test-name containment
     (`heuristic`, never invented).
"""
import re

from .. import model

RE_RUN = re.compile(r'^\s*(?://|;)\s*RUN:\s*(.+)$', re.M)
RE_FLAG = re.compile(r'(?:^|\s|-)---?([a-zA-Z][\w-]{2,})')
RE_GTEST = re.compile(r'\bTEST_F\s*\(\s*(\w+)\s*,\s*(\w+)\s*\)'
                      r'|\bTEST\s*\(\s*(\w+)\s*,\s*(\w+)\s*\)')


def extract(relpath, text):
    runs = RE_RUN.findall(text)
    gtests = [(m.group(1) and f"{m.group(1)}.{m.group(2)}")
              or f"{m.group(3)}.{m.group(4)}" for m in RE_GTEST.finditer(text)]
    if not runs and not gtests:
        return {"nodes": [], "edges": [], "diagnostics": []}
    nid = f"test:{relpath}"
    if runs:
        return _lit(relpath, text, nid, runs)
    # gtest file: node only; resolve() derives TEST_COVERS_PASS by name heuristic
    names = ", ".join(gtests[:6]) + ("..." if len(gtests) > 6 else "")
    node = {"id": nid, "kind": model.TEST, "name": relpath.rsplit("/", 1)[-1],
            "summary": f"gtest tests ({len(gtests)}): {names}",
            "file": relpath, "line": 1}
    return {"nodes": [node], "edges": [], "diagnostics": []}


def _lit(relpath, text, nid, runs):
    # coarse feature tags from filename + RUN lines + IR content (QG-5, heuristic)
    feats = set()
    hay = (relpath + " " + text).lower()
    for tag, needles in {
        "dynamic-shape": ("?", "dynamic"),
        "reduction": ("reduce", "sum(", "max(", "min("),
        "fusion": ("fused", "fusion", "merge"),
        "vectorization": ("vector<", "vector.transfer", "vectorize"),
        "bufferization": ("bufferize", "memref.alloc", "bufferization"),
        "stride-align": ("stride_align", "stride-align"),
        "nested-region": ("scf.for", "scf.if", "scf.while"),
    }.items():
        if any(n in hay for n in needles):
            feats.add(tag)
    node = {"id": nid, "kind": model.TEST, "name": relpath.rsplit("/", 1)[-1],
            "summary": "features: " + ",".join(sorted(feats)) if feats else "",
            "file": relpath, "line": 1}
    edges = []
    all_runs = "\n".join(runs)
    # pass-ish flags: -foo-bar or --foo-bar in RUN lines
    flags = set()
    for r in runs:
        for f in re.finditer(r'(?<![\w-])--?([a-z][a-z0-9-]{2,})', r):
            flags.add(f.group(1))
    for f in sorted(flags):
        if f in ("o", "S", "O", "mllvm", "pass-remarks"):
            continue
        edges.append({"src": nid, "dst": f"pass:{f}", "kind": model.TEST_COVERS_PASS,
                      "props": {}, "evidence": {"file": relpath, "line_start": 1,
                                                "line_end": 1, "snippet": all_runs[:200],
                                                "extractor": "tests",
                                                "confidence": model.HEURISTIC}})
    return {"nodes": [node], "edges": edges, "diagnostics": []}
