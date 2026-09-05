"""Pattern extractor: rewrite pattern classes, pattern set registration, op creation."""
import re

from .. import model

RE_PATTERN_CLASS = re.compile(
    r'\b(?:struct|class)\s+(\w+)\s*(?::[^{;]*)?\bpublic\s+'
    r'(OpRewritePattern|OpConversionPattern|OpInterfaceConversionPattern|'
    r'OpInterfaceRewritePattern|RewritePattern|OpTraitRewritePattern)\s*<\s*([\w:]*)')
RE_PATTERNS_ADD = re.compile(r'patterns\.add\s*<\s*([\w:\s,]+?)\s*>\s*\(')
RE_CREATE_OP = re.compile(r'(?:rewriter|builder|b)\.create\s*<\s*([\w:]+)\s*>')
RE_CONV_ADD = re.compile(r'addConversion\(')


RE_OUTOFLINE_METHOD = re.compile(
    r'\b([A-Za-z]\w*)::(runOnOperation|initialize|run)\s*\([^;{]*\)\s*(?:const\s*)?\{')


def _method_bodies(text):
    """Out-of-line member function definitions -> (class_name, start, end)."""
    out = []
    for m in RE_OUTOFLINE_METHOD.finditer(text):
        depth = 0
        start = m.end() - 1
        for i in range(start, len(text)):
            if text[i] == '{':
                depth += 1
            elif text[i] == '}':
                depth -= 1
                if depth == 0:
                    out.append((m.group(1), start, i))
                    break
    return out


def _class_bodies(text):
    """Yield (class_name, match, body_start, body_end) for classes with brace tracking."""
    out = []
    for m in re.finditer(r'\b(?:struct|class)\s+(\w+)\b[^{;]*\{', text):
        depth = 0
        start = m.end() - 1
        for i in range(start, len(text)):
            if text[i] == '{':
                depth += 1
            elif text[i] == '}':
                depth -= 1
                if depth == 0:
                    out.append((m.group(1), m, start, i))
                    break
    return out


def extract(relpath, text):
    nodes, edges = [], []
    bodies = _class_bodies(text) + [(n, None, s, e) for n, s, e in _method_bodies(text)]
    name_to_span = {n: (s, e) for n, m, s, e in _class_bodies(text)}

    def ev(start, end, conf=model.CONFIRMED):
        ls = text[:start].count("\n") + 1
        le = text[:end].count("\n") + 1
        return {"file": relpath, "line_start": ls, "line_end": le,
                "snippet": text[start:min(end, start + 200)],
                "extractor": "pattern", "confidence": conf}

    for m in RE_PATTERN_CLASS.finditer(text):
        cls, base, target = m.group(1), m.group(2), m.group(3)
        nodes.append({"id": f"pattern:{cls}", "kind": model.PATTERN, "name": cls,
                      "summary": base, "file": relpath,
                      "line": text[:m.start()].count("\n") + 1})
        if target:
            edges.append({"src": f"pattern:{cls}", "dst": f"op:{target.split('::')[-1]}",
                          "kind": model.PATTERN_MATCHES_OP, "props": {},
                          "evidence": ev(m.start(), m.end())})
        span = name_to_span.get(cls)
        if span:
            s, e = span
            body = text[s:e]
            for cm in RE_CREATE_OP.finditer(body):
                edges.append({"src": f"pattern:{cls}",
                              "dst": f"op:{cm.group(1).split('::')[-1]}",
                              "kind": model.PATTERN_CREATES_OP, "props": {"direct": True},
                              "evidence": ev(s + cm.start(), s + cm.end())})

    # patterns.add<...> : attribute to the enclosing class (pass or pattern populate fn)
    for m in RE_PATTERNS_ADD.finditer(text):
        off = m.start()
        # find innermost enclosing named class
        container = None
        for n, mm, s, e in bodies:
            if s <= off <= e:
                container = n  # last match wins = innermost (bodies not nested-sorted; approximate)
        names = [x.strip().split("::")[-1] for x in m.group(1).split(",") if x.strip()]
        for n in names:
            src = None
            if container and (container in name_to_span):
                if any(p["id"].split(":")[-1] == container for p in nodes
                       if p["id"].startswith("pattern:")):
                    src = f"pattern:{container}"
                else:
                    src = f"pass_class:{container}"
            if src is None:
                continue
            edges.append({"src": src, "dst": f"pattern:{n}",
                          "kind": model.PASS_USES_PATTERN, "props": {},
                          "evidence": ev(off, m.end())})

    return {"nodes": nodes, "edges": edges, "diagnostics": []}
