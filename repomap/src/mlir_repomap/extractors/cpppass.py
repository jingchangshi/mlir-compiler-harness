"""C++ pass extractor: pass impl classes, getArgument(), factories, PassRegistration."""
import re

from .. import model

RE_PASS_CLASS = re.compile(
    r'\b(?:struct|class)\s+(\w+)\s*(?::[^{;]*)?\b(?:public\s+)?'
    r'(?:PassWrapper\s*<\s*\w+\s*,\s*(?:OperationPass|Pass)|'
    r'OperationPass|PassWrapper|PassInfoMixin|Pass)\s*<')
RE_GETARG = re.compile(
    r'StringRef\s+getArgument\(\)\s*const\s*(?:override)?\s*{\s*return\s*"([^"]+)"')
RE_FACTORY_DEF = re.compile(
    r'^\s*(?:std::unique_ptr\s*<\s*[\w:<>,\s]+>\s*|[\w:<>,\s*]+?)\bcreate(\w+)Pass\s*\([^;{]*\)\s*{',
    re.M)
RE_FACTORY_DECL = re.compile(
    r'^\s*std::unique_ptr\s*<\s*[\w:<>,\s]+>\s*create(\w+)Pass\s*\([^;{]*\)\s*;', re.M)
RE_PASS_REG = re.compile(r'\bPassRegistration\s*<\s*(\w+)\s*>')
RE_ANALYSIS = re.compile(r'\b(?:class|struct)\s+(\w+)\s*:\s*public\s+\w*Analysis\s*<')


def extract(relpath, text):
    nodes, edges = [], []
    lines = text.split("\n")

    def ev(start_idx, end_idx=None):
        s = "\n".join(lines[start_idx - 1:(end_idx or start_idx)])
        return {"file": relpath, "line_start": start_idx, "line_end": end_idx or start_idx,
                "snippet": s, "extractor": "cpppass", "confidence": model.CONFIRMED}

    def line_of(pos):
        return text[:pos].count("\n") + 1

    # pass implementation classes
    for m in RE_PASS_CLASS.finditer(text):
        cls = m.group(1)
        ln = line_of(m.start())
        # find getArgument within the class body (crude: next 120 lines)
        body = "\n".join(lines[ln - 1: ln + 119])
        arg = None
        ma = RE_GETARG.search(body)
        if ma:
            arg = ma.group(1)
        if arg:
            nid = f"pass:{arg}"
            nodes.append({"id": nid, "kind": model.PASS, "name": arg,
                          "summary": "", "file": relpath, "line": ln})
            nodes.append({"id": f"pass_class:{cls}", "kind": model.PASS_CLASS,
                          "name": cls, "summary": "", "file": relpath, "line": ln})
            edges.append({"src": nid, "dst": f"pass_class:{cls}",
                          "kind": model.PASS_IMPLEMENTS, "props": {},
                          "evidence": ev(ln, ln + (ma and body[:ma.end()].count("\n") or 0))})
            edges.append({"src": f"file:{relpath}", "dst": nid, "kind": model.DEFINES,
                          "props": {"cpp_class": cls}, "evidence": ev(ln)})

    # factory definitions
    for m in RE_FACTORY_DEF.finditer(text):
        name = f"create{m.group(1)}Pass"
        ln = line_of(m.start())
        nodes.append({"id": f"factory:{name}", "kind": model.FACTORY, "name": name,
                      "summary": "", "file": relpath, "line": ln})
        edges.append({"src": f"file:{relpath}", "dst": f"factory:{name}",
                      "kind": model.DEFINES, "props": {}, "evidence": ev(ln)})

    # explicit registrations
    for m in RE_PASS_REG.finditer(text):
        cls = m.group(1)
        ln = line_of(m.start())
        nodes.append({"id": f"pass_class:{cls}", "kind": model.PASS_CLASS, "name": cls,
                      "summary": "", "file": relpath, "line": ln})
        edges.append({"src": f"pass_class:{cls}", "dst": f"file:{relpath}",
                      "kind": model.REFERENCES, "props": {"via": "PassRegistration"},
                      "evidence": ev(ln)})

    # analysis classes (name-level only, MVP limitation)
    for m in RE_ANALYSIS.finditer(text):
        name = m.group(1)
        ln = line_of(m.start())
        nodes.append({"id": f"symbol:{name}", "kind": model.SYMBOL, "name": name,
                      "summary": "analysis", "file": relpath, "line": ln})

    return {"nodes": nodes, "edges": edges, "diagnostics": []}
