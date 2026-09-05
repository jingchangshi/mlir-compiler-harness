"""Python pipeline-composition extractor (language-agnostic by design).

Identifies functions that compose pass pipelines in Python by signature/body, not name:
a function that references a pass-manager-like object (`pm`/`pass_manager`) and calls
`<x>.add_*(pm...)` or `pm.run(...)` becomes a pipeline-composition function node. Calls
to binding-exposed stage names (`add_*` via PyBind wrappers) emit PYTHON_COMPOSES edges
resolved at graph level.
"""
import ast
import re

from .. import model

RE_PM_CALL = re.compile(r'\b(pm|pass_manager|passmanager)\s*\.\s*(add|run|nest)\b', re.I)
RE_STAGE_CALL = re.compile(r'\b([A-Za-z_][\w.]*)\.(add_[a-z0-9_]+)\s*\(')
RE_PM_PARAM = re.compile(r'\b(pm|pass_manager|passmanager)\b', re.I)


def extract(relpath, text):
    nodes, edges, diags = [], [], []
    try:
        tree = ast.parse(text.lstrip("\ufeff"))  # BOM'd files are common in vendor trees
    except SyntaxError as e:
        return {"nodes": [], "edges": [],
                "diagnostics": [{"file": relpath, "message": f"python parse: {e!r}"}]}

    def ev(sl, el, conf=model.CONFIRMED):
        return {"file": relpath, "line_start": sl, "line_end": el,
                "snippet": text.split("\n")[sl - 1:el][0] if sl <= el else "",
                "extractor": "python", "confidence": conf}

    composers = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        seg = ast.get_source_segment(text, node) or ""
        param_names = [a.arg for a in node.args.args + node.args.kwonlyargs]
        is_composer = bool(RE_PM_PARAM.search(" ".join(param_names))) or (
            any(RE_PM_PARAM.search(t.id) for t in ast.walk(node)
                if isinstance(t, ast.Name)) and RE_PM_CALL.search(seg))
        if not is_composer:
            continue
        fid = f"function:{relpath}:{node.name}"
        composers.append((fid, node.lineno, node.end_lineno))
        summary = "pipeline composition function (Python)"
        if re.search(r'\bpm\s*\.\s*run\s*\(', seg):
            summary += " · calls pm.run"
        nodes.append({"id": fid, "kind": model.FUNCTION, "name": node.name,
                      "summary": summary, "file": relpath, "line": node.lineno})

    for fid, sl, el in composers:
        seg = "\n".join(text.split("\n")[sl - 1:el])
        for m in RE_STAGE_CALL.finditer(seg):
            bind = m.group(2)
            off_line = sl + seg[:m.start()].count("\n")
            edges.append({"src": fid, "dst": f"binding:NAME:{bind}",
                          "kind": model.PYTHON_COMPOSES,
                          "props": {"receiver": m.group(1)},
                          "evidence": ev(off_line, off_line)})
    return {"nodes": nodes, "edges": edges, "diagnostics": diags}
