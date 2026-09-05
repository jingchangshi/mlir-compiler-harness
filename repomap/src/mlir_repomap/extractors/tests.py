"""Lit/FileCheck test extractor. Coverage is name/flag matching => heuristic confidence."""
import re

from .. import model

RE_RUN = re.compile(r'^\s*(?://|;)\s*RUN:\s*(.+)$', re.M)
RE_FLAG = re.compile(r'(?:^|\s|-)---?([a-zA-Z][\w-]{2,})')


def extract(relpath, text):
    runs = RE_RUN.findall(text)
    if not runs:
        return {"nodes": [], "edges": [], "diagnostics": []}
    nid = f"test:{relpath}"
    node = {"id": nid, "kind": model.TEST, "name": relpath.rsplit("/", 1)[-1],
            "summary": "", "file": relpath, "line": 1}
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
