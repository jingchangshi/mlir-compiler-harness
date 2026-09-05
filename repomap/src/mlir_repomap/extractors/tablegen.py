"""TableGen structural extractor: dialects, passes, ops, types, attrs, interfaces.

Deliberately not a TableGen compiler (ADR: structural parse with evidence only).
"""
import re

from .. import model

RE_DIALECT = re.compile(r'^\s*def\s+(\w+?)_?Dialect\s*:\s*Dialect\b', re.M)
RE_DIALECT2 = re.compile(r'^\s*def\s+(\w+)\s*:\s*Dialect\b', re.M)
RE_PASS = re.compile(r'^\s*def\s+(\w+)\s*:\s*Pass\s*<\s*"([^"]+)"\s*(?:,\s*"([^"]*)")?', re.M)
RE_OP = re.compile(r'^\s*def\s+(\w+)\s*:\s*Op\s*<\s*([\w]+(?:\.[\w]+)*)\s*,\s*"([^"]+)"', re.M)
# dialect-specific multiclass aliases: def FooOp : HIVM_Op<"name", ...>
RE_OP_ALIAS = re.compile(r'^\s*def\s+(\w+)\s*:\s*(\w+)_Op\s*<\s*"([^"]+)"', re.M)
RE_TYPEDEF = re.compile(r'^\s*def\s+(\w+)\s*:\s*TypeDef\s*<\s*(\w+)', re.M)
RE_ATTRDEF = re.compile(r'^\s*def\s+(\w+)\s*:\s*AttrDef\s*<\s*(\w+)', re.M)
RE_IFACE = re.compile(r'^\s*def\s+(\w+)\s*:\s*(?:Default|Declare\w*)?\s*(?:Op|Type|Attr)?Interface\s*<', re.M)
# let/dag/multiclass noise guard: only accept def lines at brace depth 0 handled by caller lazily


def _summary_after(src, m):
    """Take a short summary from the text right after a td def header."""
    tail = src[m.end():m.end() + 400]
    sm = re.search(r'"([^"\n]{10,200})"', tail)
    if sm and 'let' not in src[m.end():m.end() + sm.start() + 1][:40]:
        return sm.group(1)
    return ""


def extract(relpath, text):
    nodes, edges, diags = [], [], []
    ev = lambda m: {"file": relpath, "line_start": text[:m.start()].count("\n") + 1,
                    "line_end": text[:m.end()].count("\n") + 1,
                    "snippet": m.group(0), "extractor": "tablegen",
                    "confidence": model.CONFIRMED}

    dialects = {}  # tblgen class name prefix -> dialect node id

    for m in RE_DIALECT.finditer(text):
        name = m.group(1)
        nid = f"dialect:{name}"
        nodes.append({"id": nid, "kind": model.DIALECT, "name": name,
                      "summary": _summary_after(text, m), "file": relpath,
                      "line": ev(m)["line_start"]})
        dialects[f"{name}"] = nid
        edges.append({"src": f"file:{relpath}", "dst": nid, "kind": model.DEFINES,
                      "props": {}, "evidence": ev(m)})

    pass_matches = list(RE_PASS.finditer(text))
    for i, m in enumerate(pass_matches):
        cls, arg = m.group(1), m.group(2)
        # region of this def: up to the next top-level def
        end = pass_matches[i + 1].start() if i + 1 < len(pass_matches) else len(text)
        region = text[m.start():end]
        sm = re.search(r'let summary\s*=\s*"([^"]*)"', region)
        summary = sm.group(1) if sm else ""
        nid = f"pass:{arg}"
        nodes.append({"id": nid, "kind": model.PASS, "name": arg, "summary": summary,
                      "file": relpath, "line": ev(m)["line_start"]})
        edges.append({"src": f"file:{relpath}", "dst": nid, "kind": model.DEFINES,
                      "props": {"tblgen_class": cls}, "evidence": ev(m)})
        # the authoritative factory link: let constructor = "ns::createXxxPass()"
        cm = re.search(r'let constructor\s*=\s*"([^"]*?)\bcreate(\w+)Pass\s*\(\)"', region)
        if cm:
            fac = f"create{cm.group(2)}Pass"
            nodes.append({"id": f"factory:{fac}", "kind": model.FACTORY, "name": fac,
                          "summary": "", "file": relpath,
                          "line": ev(m)["line_start"] + region[:cm.start()].count("\n")})
            edges.append({"src": nid, "dst": f"factory:{fac}",
                          "kind": model.PASS_HAS_FACTORY, "props": {},
                          "evidence": ev(m)})

    def _owning_dialect(prefix):
        # e.g. HIVM_LoadOp -> HIVM ; also plain class refs like SimpleDialect -> Simple
        for cand in (prefix[:-len("Dialect")] if prefix.endswith("Dialect") else None,
                     prefix):
            if cand and cand in dialects:
                return dialects[cand]
        parts = prefix.split("_")
        for i in range(len(parts) - 1, 0, -1):
            cand = "_".join(parts[:i])
            if cand in dialects:
                return dialects[cand]
        return None

    op_matches = [(m, m.group(1), m.group(2), m.group(3)) for m in RE_OP.finditer(text)]
    op_matches += [(m, m.group(1), m.group(2) + "_Dialect", m.group(3))
                   for m in RE_OP_ALIAS.finditer(text)]
    for m, cls, dialect_ref, opname in op_matches:
        nid = f"op:{cls}"
        nodes.append({"id": nid, "kind": model.OP, "name": opname,
                      "summary": _summary_after(text, m), "file": relpath,
                      "line": ev(m)["line_start"]})
        owner = _owning_dialect(dialect_ref)
        if owner:
            edges.append({"src": owner, "dst": nid, "kind": model.DIALECT_OWNS,
                          "props": {}, "evidence": ev(m)})
        edges.append({"src": f"file:{relpath}", "dst": nid, "kind": model.DEFINES,
                      "props": {}, "evidence": ev(m)})

    for regex, kind, tag in ((RE_TYPEDEF, model.TYPE, "typedef"),
                             (RE_ATTRDEF, model.ATTR, "attrdef"),
                             (RE_IFACE, model.INTERFACE, "interface")):
        for m in regex.finditer(text):
            name = m.group(1)
            nid = f"{kind}:{name}"
            nodes.append({"id": nid, "kind": kind, "name": name, "summary": "",
                          "file": relpath, "line": ev(m)["line_start"]})
            if kind != model.INTERFACE and len(m.groups()) > 1:
                owner = _owning_dialect(m.group(2))
                if owner:
                    edges.append({"src": owner, "dst": nid, "kind": model.DIALECT_OWNS,
                                  "props": {}, "evidence": ev(m)})

    return {"nodes": nodes, "edges": edges, "diagnostics": diags}
