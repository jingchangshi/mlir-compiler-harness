"""Attribute creator provenance (Phase 15 / RG-1, ADR-021).

For every IR attribute reference (`XxxAttr::name` / `kXxxAttr` idiom) in C++
text, classify the enclosing container and emit typed provenance edges.
Node discovery (`attribute:<X>` nodes + file-level REFERENCES) stays in
cpppass.py; this module only types containers, so it never emits attribute
nodes.

Creator typing is container classification (deterministic, brace-matched):

  container                                   -> edge
  pattern class, conversion base              -> CREATES_ATTRIBUTE creator_type=ConversionPattern
  other rewrite-pattern class                 -> CREATES_ATTRIBUTE creator_type=RewritePattern
  op `build` method (qualified definition)    -> CREATES_ATTRIBUTE creator_type=OpBuilder
  pass class / pass class method              -> CREATES_ATTRIBUTE creator_type=Pass
  pipeline builder function (OpPassManager)   -> CREATES_ATTRIBUTE creator_type=PipelineBuilder
  verifier method creating/attaching          -> CREATES_ATTRIBUTE creator_type=Verifier
  verifier method reading                     -> REFERENCES role=verifier
  other container reading                     -> REFERENCES role=reader

A reference line containing `setAttr(`/`addAttr(` is an attachment site
(`attach: true`); `XxxAttr::get(` marks construction. Read-only lines
(`getAttr(`/`removeAttr(`/`hasAttr(`/plain mention) are consumers, never
creators — a mere mention does not prove creation.
"""

import re

from .. import model
from .cpppass import RE_PASS_CLASS
from .pattern import RE_PATTERN_CLASS

RE_ATTR_NAME = re.compile(r'\b(\w+Attr)::name|\bk([A-Z]\w*Attr)\b')
RE_METHOD = re.compile(
    r'\b([A-Za-z]\w*)::([A-Za-z]\w*)\s*\([^;{]*\)\s*(?:const\s*)?\{')
RE_FUNC_DEF = re.compile(
    r'^(?:static\s+)?(?:void|LogicalResult|mlir::LogicalResult|bool)\s+'
    r'(\w+)\s*\(', re.M)
RE_CREATE = re.compile(r'\b(\w+Attr)::get\s*\(')
RE_ATTACH = re.compile(r'\b(?:setAttr|addAttr(?:ibute)?)\s*\(')
RE_READ = re.compile(r'\b(?:getAttr|removeAttr|hasAttr)\s*\(')


def _brace_span(text, start):
    """Return (start, end) offsets of the brace block opening at `start`."""
    d = 0
    for i in range(start, len(text)):
        if text[i] == "{":
            d += 1
        elif text[i] == "}":
            d -= 1
            if d == 0:
                return (start, i)
    return None


def extract(relpath, text):
    nodes, edges = [], []
    line_of = lambda pos: text[:pos].count("\n") + 1

    def ev(pos):
        return {"file": relpath, "line_start": line_of(pos), "line_end": line_of(pos),
                "snippet": text.split("\n")[line_of(pos) - 1].strip()[:140],
                "extractor": "attribute", "confidence": model.INFERRED}

    # collect hits: (name, pos)
    hits = []
    for m in RE_ATTR_NAME.finditer(text):
        hits.append((m.group(1) or m.group(2), m.start()))
    if not hits:
        return nodes, edges, []

    containers = []  # (start, end, container_id, creator_type|None, kind_hint)

    # pattern classes (base decides RewritePattern vs ConversionPattern)
    for m in RE_PATTERN_CLASS.finditer(text):
        ob = text.find("{", m.end())
        span = _brace_span(text, ob) if ob != -1 else None
        if not span:
            continue
        base = m.group(2) or ""
        ctype = "ConversionPattern" if "Conversion" in base else "RewritePattern"
        containers.append((span[0], span[1], f"pattern:{m.group(1)}", ctype,
                           "class"))
    # pass implementation classes
    for m in RE_PASS_CLASS.finditer(text):
        ob = text.find("{", m.end())
        span = _brace_span(text, ob) if ob != -1 else None
        if not span:
            continue
        containers.append((span[0], span[1], f"pass_class:{m.group(1)}", "Pass",
                           "class"))
    pattern_classes = {c[2].split(":", 1)[1]: c[3] for c in containers
                       if c[2].startswith("pattern:")}
    pass_classes = {c[2].split(":", 1)[1] for c in containers
                    if c[2].startswith("pass_class:")}

    # out-of-line (and inline) methods: Class::method(...) { ... }
    for m in RE_METHOD.finditer(text):
        cls, meth = m.group(1), m.group(2)
        span = _brace_span(text, m.end() - 1)
        if not span:
            continue
        if cls in pattern_classes:
            containers.append((span[0], span[1], f"pattern:{cls}",
                               pattern_classes[cls], "method"))
        elif cls in pass_classes:
            containers.append((span[0], span[1], f"pass_class:{cls}", "Pass",
                               "method"))
        elif meth == "build":
            nodes.append({"id": f"symbol:{cls}", "kind": model.SYMBOL,
                          "name": cls, "summary": "op class (build method)",
                          "file": relpath, "line": line_of(m.start())})
            containers.append((span[0], span[1], f"symbol:{cls}", "OpBuilder",
                               "method"))
        elif meth.startswith("verify"):
            nodes.append({"id": f"symbol:{cls}", "kind": model.SYMBOL,
                          "name": cls, "summary": "verifier container",
                          "file": relpath, "line": line_of(m.start())})
            containers.append((span[0], span[1], f"symbol:{cls}", None,
                               "verifier"))

    # pipeline builder functions: OpPassManager param + builds (mirrors
    # pipeline.py's qualification so the function node id matches)
    for m in RE_FUNC_DEF.finditer(text):
        pe = text.find(")", m.end())
        if pe == -1:
            continue
        params = text[m.end():pe]
        if "OpPassManager" not in params:
            continue
        ob = text.find("{", pe)
        if ob == -1 or text[pe:ob].count(";") > 2:
            continue
        span = _brace_span(text, ob)
        if not span:
            continue
        body = text[span[0]:span[1]]
        if "addPass(" not in body and ".nest<" not in body:
            continue
        fname = m.group(1)
        nodes.append({"id": f"function:{relpath}:{fname}", "kind": model.FUNCTION,
                      "name": fname, "summary": "pipeline builder",
                      "file": relpath, "line": line_of(ob)})
        containers.append((span[0], span[1], f"function:{relpath}:{fname}",
                           "PipelineBuilder", "function"))

    # pattern-side helpers: free functions taking PatternRewriter& /
    # ConversionPatternRewriter& (signature rule, same principle as the
    # RewritePatternSet& populator rule in pattern.py)
    for m in RE_FUNC_DEF.finditer(text):
        pe = text.find(")", m.end())
        if pe == -1:
            continue
        params = text[m.end():pe]
        if "PatternRewriter" not in params:
            continue
        ob = text.find("{", pe)
        if ob == -1 or text[pe:ob].count(";") > 2:
            continue
        span = _brace_span(text, ob)
        if not span:
            continue
        fname = m.group(1)
        ctype = ("ConversionPattern"
                 if "ConversionPatternRewriter" in params else "RewritePattern")
        nodes.append({"id": f"function:{relpath}:{fname}", "kind": model.FUNCTION,
                      "name": fname, "summary": "pattern helper",
                      "file": relpath, "line": line_of(ob)})
        containers.append((span[0], span[1], f"function:{relpath}:{fname}",
                           ctype, "function"))

    # innermost container wins: sort by span size ascending
    containers.sort(key=lambda c: c[1] - c[0])

    def _container(pos):
        for c0, c1, cid, ctype, hint in containers:
            if c0 <= pos <= c1:
                return cid, ctype, hint
        return None, None, None

    for name, pos in hits:
        cid, ctype, hint = _container(pos)
        if cid is None:
            continue  # unattributed: file-level REFERENCES (cpppass.py) covers it
        line = text.split("\n")[line_of(pos) - 1]
        creates = RE_CREATE.search(line) is not None
        attaches = RE_ATTACH.search(line) is not None
        reads = RE_READ.search(line) is not None
        if creates or attaches:
            ct = ctype if ctype else "Verifier"
            edges.append({"src": cid, "dst": f"attribute:{name}",
                          "kind": model.CREATES_ATTRIBUTE,
                          "props": {"creator_type": ct, "attach": attaches},
                          "evidence": ev(pos)})
        elif reads or hint in ("verifier",):
            role = "verifier" if hint == "verifier" else "reader"
            edges.append({"src": cid, "dst": f"attribute:{name}",
                          "kind": model.REFERENCES,
                          "props": {"role": role, "via": "Attr-ref"},
                          "evidence": ev(pos)})
    return {"nodes": nodes, "edges": edges, "diagnostics": []}
