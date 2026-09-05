"""Pipeline extractor: addPass/addNestedPass/nest<> with ordering, nesting and guards.

Conditional membership (ADR-002): an `if (...) { pm.addPass(A); }` produces a
PIPELINE_CONTAINS edge whose props carry the guard expression; `#if MACRO` guards are
recorded with condition_kind="macro". Preprocessor tracking is per function body.
"""
import re

from .. import model

RE_FUNC = re.compile(
    r'^(?:static\s+)?(?:void|LogicalResult|mlir::LogicalResult|bool)\s+'
    r'(?:(\w+)::)?(\w+)\s*\(', re.M)
RE_ADDPASS = re.compile(r'(?:(\w+)\.)?\b(addPass|addNestedPass)\(\s*([^;]{0,200}?)\s*\);')
RE_NEST = re.compile(r'\.nest\s*<\s*([\w:]+)\s*>')
RE_IF = re.compile(r'\bif\s*\(')
RE_CALL_BUILD = re.compile(r'\b((?:\w+::)*)(build\w*(?:Pipeline|s)?|run\w*(?:Compile|Pipeline)?)\s*\(')
RE_FACTORY_CALL = re.compile(r'create(\w+)Pass')
RE_PASSCTOR = re.compile(r'\b(\w+Pass)\s*\(')
RE_PP_IF = re.compile(r'^\s*#\s*(if|ifdef|ifndef)\s+(.+?)\s*$', re.M)
RE_PP_ENDIF = re.compile(r'^\s*#\s*endif', re.M)


def _match_brace(text, open_idx):
    depth = 0
    for i in range(open_idx, len(text)):
        c = text[i]
        if c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
            if depth == 0:
                return i
    return len(text) - 1


def _params_end(text, paren_idx):
    depth = 0
    for i in range(paren_idx, len(text)):
        if text[i] == '(':
            depth += 1
        elif text[i] == ')':
            depth -= 1
            if depth == 0:
                return i
    return paren_idx


def _extract_pass_dst(call_text):
    """Best-effort pass reference from an addPass argument."""
    m = RE_FACTORY_CALL.search(call_text)
    if m:
        return f"factory:create{m.group(1)}Pass", model.CONFIRMED
    m = RE_PASSCTOR.search(call_text)
    if m:
        return f"cppclass:{m.group(1)}", model.INFERRED
    return None, None


def extract(relpath, text):
    nodes, edges, diags = [], [], []
    lines = text.split("\n")

    def ev(start_pos, end_pos, conf=model.CONFIRMED):
        ls = text[:start_pos].count("\n") + 1
        le = text[:end_pos].count("\n") + 1
        return {"file": relpath, "line_start": ls, "line_end": le,
                "snippet": text[start_pos:end_pos], "extractor": "pipeline",
                "confidence": conf}

    functions = []  # (name, class, body_start, body_end)
    for m in RE_FUNC.finditer(text):
        pe = _params_end(text, m.end() - 1)
        # find opening brace of body (skip initializer lists)
        ob = text.find("{", pe)
        if ob == -1 or text[pe:ob].count(";") > 2:
            continue
        cb = _match_brace(text, ob)
        body = text[ob:cb]
        if "addPass(" in body or ".nest<" in body:
            functions.append((m.group(2), m.group(1), ob, cb))
        elif RE_CALL_BUILD.search(body):
            # small dispatch functions still count as pipelines when they build pipelines
            pass

    for fname, cls, ob, cb in functions:
        pid = f"pipeline:{fname}"
        nodes.append({"id": pid, "kind": model.PIPELINE, "name": fname, "summary": "",
                      "file": relpath, "line": text[:ob].count("\n") + 1})
        body = text[ob:cb + 1]
        base = ob

        # preprocessor guard map for the body
        pp_stack = []  # (end_pos, name)
        pp_guards = []  # (start_offset, end_offset, name)
        for m in RE_PP_IF.finditer(body):
            pp_stack.append((m, m.group(2).strip()))
        for m in RE_PP_ENDIF.finditer(body):
            if pp_stack:
                opened, name = pp_stack.pop()
                pp_guards.append((opened.end(), m.start(), name))

        def macro_guard_at(off):
            g = None
            for s, e, name in pp_guards:
                if s <= off < e:
                    g = name  # innermost wins (later ranges processed last)
            return g

        # structural scan of body: record if-guard intervals [start, end]
        events = []
        guards = []   # ["if", start_off, end_off, cond]
        open_ifs = []  # body-open offsets of currently-open if blocks
        i = 0
        stack = []
        while i < len(body):
            ch = body[i]
            if body.startswith("if", i) and RE_IF.match(body, i):
                # capture condition parens
                po = body.find("(", i)
                pe2 = _params_end(body, po)
                cond = body[po + 1:pe2].strip().replace("\n", " ")[:160]
                bo = body.find("{", pe2)
                # if without braces: applies to next statement only
                if bo != -1 and body[pe2:bo].count(";") == 0:
                    open_ifs.append(bo)
                    guards.append(["if", bo, None, cond])
                    i = bo
                else:
                    events.append(("one_stmt_if", i, i + len(body[i:pe2 + 1]), cond))
                    i = pe2
                continue
            if ch == "{":
                if not open_ifs or open_ifs[-1] != i:
                    pass  # plain block: guards unchanged
            elif ch == "}":
                if open_ifs:
                    bo = open_ifs.pop()
                    for g in reversed(guards):
                        if g[1] == bo and g[2] is None:
                            g[2] = i
                            break
            i += 1
        for g in guards:
            if g[2] is None:
                g[2] = len(body) - 1

        def cond_at(off):
            cond, kind = None, "config"
            for k, s, e, c in guards:
                if k == "if" and s <= off <= e:
                    cond = c
            mg = macro_guard_at(off)
            if mg:
                cond = f"#if {mg}: {cond}" if cond else f"#if {mg}"
                kind = "macro"
            return cond, kind

        # order counter per scope
        scope_orders = {}
        scope_stack = ["module"]
        # walk addPass occurrences in order
        last_pass_by_scope = {}
        for m in RE_ADDPASS.finditer(body):
            off = m.start()
            mgr, method, arg = m.group(1), m.group(2), m.group(3)
            # nesting: manager var may be a nest<> chain result captured earlier; also inline
            # pm.nest<Op>().addPass(...) — detect nest in preceding 80 chars
            pre = body[max(0, off - 120):off]
            nm = RE_NEST.findall(pre) or RE_NEST.findall(arg[:60])
            # conservative: only track nest from `= ...nest<Op>()` or inline chain
            inline_nest = RE_NEST.search(body[max(0, off - 60):off])
            scope = "module"
            if inline_nest:
                scope = inline_nest.group(1)
            else:
                # find latest `X = pm.nest<Op>();` before this call
                for nm2 in re.finditer(r'(\w+)\s*=\s*[\w.]+\.nest\s*<\s*([\w:]+)\s*>', body[:off]):
                    if mgr == nm2.group(1):
                        scope = nm2.group(2)
            dst, conf = _extract_pass_dst(arg)
            if dst is None:
                diags.append({"file": relpath,
                              "message": f"unresolved addPass arg: {arg[:80]}"})
                continue
            key = scope if method == "addPass" else f"{scope}:nested"
            scope_orders[key] = scope_orders.get(key, 0) + 1
            cond, ckind = cond_at(off)
            props = {"order": scope_orders[key], "scope": scope, "nested": method == "addNestedPass"}
            if cond:
                props["condition"] = cond
                props["condition_kind"] = ckind
            edges.append({"src": pid, "dst": dst, "kind": model.PIPELINE_CONTAINS,
                          "props": props, "evidence": ev(base + off, base + m.end(), conf)})
            prev = last_pass_by_scope.get(key)
            if prev:
                edges.append({"src": prev, "dst": dst, "kind": model.PRECEDES,
                              "props": {"pipeline": fname, "scope": key},
                              "evidence": ev(base + off, base + m.end(), model.CONFIRMED)})
            last_pass_by_scope[key] = dst

        # calls to other pipeline builders
        for m in RE_CALL_BUILD.finditer(body):
            callee = m.group(2)
            if callee == fname:
                continue
            # only treat as sub-pipeline if name looks like a builder and another
            # function with this name exists (resolver dedups); emit with confidence
            if callee.startswith(("build", "run")):
                edges.append({"src": pid, "dst": f"pipeline:{callee}",
                              "kind": model.PIPELINE_CALLS, "props": {},
                              "evidence": ev(base + m.start(), base + m.end(),
                                             model.INFERRED)})

    return {"nodes": nodes, "edges": edges, "diagnostics": diags}
