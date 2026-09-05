"""C++ pass extractor: pass impl classes, getArgument(), factories, PassRegistration."""
import re

from .. import model

RE_PASS_CLASS = re.compile(
    r'\b(?:struct|class)\s+(\w+)\s*(?::[^{;]*)?\b(?:public\s+)?'
    r'(?:PassWrapper\s*<\s*\w+\s*,\s*(?:OperationPass|Pass)|'
    r'OperationPass|PassWrapper|PassInfoMixin|(?:impl\s*::\s*)?(\w+Base)|Pass)\s*<')
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
        elif m.group(2):
            # generated-base idiom (impl::<TdClass>Base<Concrete>): no getArgument here.
            # Emit a cpp_class mapping; resolve() bridges it via the td tblgen_class.
            nodes.append({"id": f"pass_class:{cls}", "kind": model.PASS_CLASS,
                          "name": cls, "summary": "", "file": relpath, "line": ln})
            edges.append({"src": f"file:{relpath}", "dst": f"pass_class:{cls}",
                          "kind": model.DEFINES,
                          "props": {"cpp_class": cls, "impl_base": m.group(2)},
                          "evidence": ev(ln)})

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

    # Optimization-constraint extraction (Phase 12): legality guards inside pass
    # implementation classes and their out-of-line method bodies. Deterministic:
    # condition text + reason string + evidence line; no interpretation.
    RE_FAIL = re.compile(r'(?:return\s+)?(?:failure\s*\(|WalkResult::skip\s*\(\)|'
                         r'signalPassFailure\s*\(\))|notifyMatchFailure\s*\(')
    RE_REASON = re.compile(r'notifyMatchFailure\s*\([^;]*?"([^"\n]{3,140})"')
    lines_all = text.split("\n")

    class_spans = []
    for m in RE_PASS_CLASS.finditer(text):
        start = text.find("{", m.start())
        d = 0
        for i in range(start, len(text)):
            if text[i] == "{":
                d += 1
            elif text[i] == "}":
                d -= 1
                if d == 0:
                    class_spans.append((m.group(1), start, i))
                    break
    cls_names = {c for c, _, _ in class_spans}
    method_spans = []
    for m in re.finditer(
            r'\b([A-Za-z]\w*)::([A-Za-z]\w*)\s*\([^;{]*\)\s*(?:const\s*)?\{', text):
        if m.group(1) in cls_names:
            start = m.end() - 1
            d = 0
            for i in range(start, len(text)):
                if text[i] == "{":
                    d += 1
                elif text[i] == "}":
                    d -= 1
                    if d == 0:
                        method_spans.append((m.group(1), start, i))
                        break

    def _emit(cid, name, summary, cls_name, off, kind, ln):
        nodes.append({"id": cid, "kind": model.CONSTRAINT, "name": name,
                      "summary": summary[:140], "file": relpath, "line": ln})
        edges.append({"src": f"pass_class:{cls_name}", "dst": cid,
                      "kind": model.HAS_CONSTRAINT, "props": {"kind": kind},
                      "evidence": ev(ln)})

    for cls_name, s0, e0 in class_spans + method_spans:
        body = text[s0:e0]
        base_line = text[:s0].count("\n") + 1
        seen_offs = set()
        # notifyMatchFailure with literal reason
        for m in RE_REASON.finditer(body):
            off = base_line + body[:m.start()].count("\n")
            seen_offs.add(off)
            _emit(f"constraint:{relpath}:{off}", f"match-failure @ line {off}",
                  m.group(1), cls_name, off, "match-failure", off)
        # failure/skip/signalPassFailure guards
        for m in RE_FAIL.finditer(body):
            off = base_line + body[:m.start()].count("\n")
            if off in seen_offs:
                continue
            cond = None
            for back in range(1, 4):
                idx = off - back
                if idx < 1:
                    break
                line = lines_all[idx - 1].strip()
                if line.startswith("if ") or line.startswith("} else if ") or \
                        line.startswith("else if") or " if (" in line:
                    po = line.find("(")
                    if po != -1:
                        cond = line[po + 1:].rstrip("){ ").strip()[:140]
                    break
            if "notifyMatchFailure" in m.group(0):
                continue  # reasonless notifyMatchFailure: skip (reason ones captured)
            if "signalPassFailure" in m.group(0) and not cond:
                ctx = ""
                for back in range(1, 4):
                    idx = off - back
                    if idx < 1:
                        break
                    line = lines_all[idx - 1].strip()
                    if line and not line.startswith("//"):
                        ctx = line[:140]
                        break
                _emit(f"constraint:{relpath}:{off}", f"pass-failure @ line {off}",
                      ctx or "signalPassFailure", cls_name, off, "pass-failure", off)
                continue
            if not cond:
                continue
            kind = ("legality-guard" if "failure" in m.group(0).lower()
                    else "early-return")
            _emit(f"constraint:{relpath}:{off}", f"{kind} @ line {off}",
                  cond, cls_name, off, kind, off)

    # PyBind-style binding boundary (Phase 9): a string name mapped to a C++ function,
    # via m.def("name", fn) / WRAPPER-style macros ("name", fn), OR via m.def("name",
    # [](PassManager &pm){ ... createXPass() ... }) lambdas whose body holds the factory.
    for m in re.finditer(r'\bm\.def\(\s*"([a-z0-9_]+)"', text):
        bind = m.group(1)
        ln = line_of(m.start())
        nodes.append({"id": f"binding:{bind}", "kind": model.BINDING, "name": bind,
                      "summary": "binding boundary", "file": relpath, "line": ln})
        # lambda form: m.def("name", [](args...) { ... createXPass(...) ... });
        lam = re.search(r'\[\s*\]\s*\(', text[m.end():m.end() + 400])
        if lam:
            body_open = m.end() + text[m.end():m.end() + 400].find('{')                 if '{' in text[m.end():m.end() + 400] else -1
            if body_open == -1:
                seg = text[m.end():m.end() + 400]
            else:
                depth = 0
                close = body_open
                for i in range(body_open, min(body_open + 4000, len(text))):
                    if text[i] == '{':
                        depth += 1
                    elif text[i] == '}':
                        depth -= 1
                        if depth == 0:
                            close = i
                            break
                seg = text[body_open:close]
            fm = re.search(r'\bcreate(\w+Pass)\s*\(', seg)
            if fm:
                edges.append({"src": f"binding:{bind}",
                              "dst": f"factory:create{fm.group(1)}",
                              "kind": model.BINDING_MAPS_TO, "props": {"via": "lambda"},
                              "evidence": ev(ln, ln + seg.count("\n"))})
            continue
        # direct function-reference form: m.def("name", createXPass)
        fm = re.search(r'"\s*,\s*([A-Za-z:][\w:]*)', text[m.end():m.end() + 200])
        if fm:
            edges.append({"src": f"binding:{bind}",
                          "dst": f"function:NAME:{fm.group(1).split('::')[-1]}",
                          "kind": model.BINDING_MAPS_TO, "props": {},
                          "evidence": ev(ln)})

    # ConversionTarget dialect transitions (Phase 10): legal = output side,
    # illegal = input side. Attributed to the nearest preceding pass class.
    class_starts = [(m.start(), m.group(1)) for m in RE_PASS_CLASS.finditer(text)]

    def _enclosing_class(pos):
        cand = None
        for p, c in class_starts:
            if p <= pos:
                cand = c
            else:
                break
        return cand

    for m in re.finditer(r'\badd(Legal|Illegal)Dialect\s*<\s*[\w:]*?(\w+?)Dialect\s*>', text):
        role, name = ("output" if m.group(1) == "Legal" else "input"), m.group(2)
        ln = line_of(m.start())
        owner = _enclosing_class(m.start())
        if not owner:
            continue
        edges.append({"src": f"pass_class:{owner}", "dst": f"dialect:{name}",
                      "kind": model.DIALECT_TRANSITIONS_TO,
                      "props": {"role": role}, "evidence": ev(ln)})
    for m in re.finditer(r'\badd(Legal|Illegal)Op\s*<\s*(\w+)\s*>', text):
        role = "output" if m.group(1) == "Legal" else "input"
        ln = line_of(m.start())
        owner = _enclosing_class(m.start())
        if not owner:
            continue
        edges.append({"src": f"pass_class:{owner}", "dst": f"op:{m.group(2)}",
                      "kind": model.DIALECT_TRANSITIONS_TO,
                      "props": {"role": role}, "evidence": ev(ln)})

    # IR attribute name references (QG-4): `XxxAttr::name` and `kXxxAttr` constants
    attr_hits = {}
    for m in re.finditer(r'\b(\w+Attr)::name', text):
        nm = m.group(1)
        ln = line_of(m.start())
        attr_hits.setdefault(nm, ln)
    for m in re.finditer(r'\bk([A-Z]\w*Attr)\b', text):
        nm = m.group(1)
        ln = line_of(m.start())
        attr_hits.setdefault(nm, ln)
    ROLES = (
        (("align", "stride"), "memory alignment contract"),
        (("core_type", "coretype", "tcore"), "core-type assignment"),
        (("annotation",), "annotation carrier"),
        (("storage_aligned",), "storage-alignment marker"),
        (("vector_function", "vf"), "vector-function marker"),
        (("layout", "layout",), "layout contract"),
        (("tiling", "tile"), "tiling contract"),
        (("sync", "barrier"), "synchronization contract"),
    )
    def _role(nm):
        low = nm.lower()
        for keys, role in ROLES:
            if any(k in low for k in keys):
                return role
        return None
    for nm, ln in sorted(attr_hits.items()):
        role = _role(nm)
        nodes.append({"id": f"attribute:{nm}", "kind": model.ATTRIBUTE, "name": nm,
                      "summary": f"role: {role} (heuristic)" if role else "",
                      "file": relpath, "line": ln})
        edges.append({"src": f"file:{relpath}", "dst": f"attribute:{nm}",
                      "kind": model.REFERENCES, "props": {"via": "Attr-ref"},
                      "evidence": ev(ln)})
    # attribute created inside a pass class body -> CREATES_ATTRIBUTE (inferred)
    for m in RE_PASS_CLASS.finditer(text):
        cls = m.group(1)
        ln = line_of(m.start())
        body = "\n".join(lines[ln - 1: ln + 199])
        for nm in attr_hits:
            if nm in body:
                edges.append({"src": f"pass_class:{cls}", "dst": f"attribute:{nm}",
                              "kind": model.CREATES_ATTRIBUTE,
                              "props": {},
                              "evidence": {**ev(ln), "confidence": model.INFERRED}})

    # analysis classes (name-level only, MVP limitation)
    for m in RE_ANALYSIS.finditer(text):
        name = m.group(1)
        ln = line_of(m.start())
        nodes.append({"id": f"symbol:{name}", "kind": model.SYMBOL, "name": name,
                      "summary": "analysis", "file": relpath, "line": ln})

    return {"nodes": nodes, "edges": edges, "diagnostics": []}
