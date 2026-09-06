"""Deterministic Python pipeline provenance extraction (ADR-024).

Python composition is a first-class ``pipeline`` when a function constructs a
pass manager, adds stages, or declares an ordered pipeline list. AST locations
are the only source of order; unresolved stage names remain explicit markers
for graph resolution and are surfaced by ``pipeline-stages`` as diagnostics.
"""
import ast
import re

from .. import model

RE_PM_NAME = re.compile(r"^(pm|pass_manager|passmanager)$", re.I)


def _dotted(node):
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = _dotted(node.value)
        return f"{base}.{node.attr}" if base else node.attr
    return ""


def _contains_pm(node, names):
    return any(isinstance(item, ast.Name) and item.id in names
               for item in ast.walk(node))


def _stage_target(node):
    """Return a deterministic marker for a statically named Python stage."""
    if isinstance(node, ast.Call):
        name = _dotted(node.func).split(".")[-1]
        if name.startswith("create") and name.endswith("Pass"):
            return f"factory:{name}", "factory"
        if name:
            return f"pass:NAME:{name}", "call"
    if isinstance(node, ast.Name):
        return f"pass:NAME:{node.id}", "name"
    if isinstance(node, ast.Attribute):
        return f"pass:NAME:{_dotted(node)}", "attribute"
    return None, None


def extract(relpath, text):
    nodes, edges = [], []
    try:
        tree = ast.parse(text.lstrip("\ufeff"))  # vendor files may carry a BOM
    except SyntaxError as e:
        return {"nodes": [], "edges": [],
                "diagnostics": [{"file": relpath, "message": f"python parse: {e!r}"}]}
    lines = text.split("\n")

    def ev(node, conf=model.CONFIRMED):
        line = getattr(node, "lineno", 1)
        end = getattr(node, "end_lineno", line)
        return {"file": relpath, "line_start": line, "line_end": end,
                "snippet": lines[line - 1] if 0 < line <= len(lines) else "",
                "extractor": "python", "confidence": conf}

    for fn in ast.walk(tree):
        if not isinstance(fn, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        params = [arg.arg for arg in fn.args.args + fn.args.kwonlyargs]
        pm_names = {name for name in params if RE_PM_NAME.match(name)}
        for item in ast.walk(fn):
            if isinstance(item, ast.Assign) and isinstance(item.value, ast.Call):
                call_name = _dotted(item.value.func).lower()
                if "pass_manager" in call_name or call_name.endswith("passmanager"):
                    pm_names.update(target.id for target in item.targets
                                    if isinstance(target, ast.Name))
        calls = sorted((item for item in ast.walk(fn) if isinstance(item, ast.Call)),
                       key=lambda item: (item.lineno, item.col_offset))
        lists = sorted((item for item in ast.walk(fn) if isinstance(item, ast.Assign)
                        and isinstance(item.value, (ast.List, ast.Tuple)) and
                        any(isinstance(target, ast.Name) and
                            ("pipeline" in target.id.lower() or
                             "stages" in target.id.lower())
                            for target in item.targets)),
                       key=lambda item: (item.lineno, item.col_offset))
        has_stage_call = any(
            isinstance(call.func, ast.Attribute) and (
                (isinstance(call.func.value, ast.Name) and
                 call.func.value.id in pm_names and
                 call.func.attr in ("add_pass", "addPass", "add_nested_pass", "addNestedPass"))
                or (call.func.attr.startswith("add_") and
                    any(_contains_pm(arg, pm_names) for arg in call.args)))
            for call in calls)
        has_cxx_pipeline_call = any(
            not isinstance(call.func, ast.Attribute) and
            (_dotted(call.func).startswith("make_") or
             (_dotted(call.func).startswith("build") and
              _dotted(call.func).endswith("Pipeline"))) and
            any(_contains_pm(arg, pm_names) for arg in call.args)
            for call in calls)
        if not pm_names or not (has_stage_call or lists or has_cxx_pipeline_call):
            continue

        fid = f"function:{relpath}:{fn.name}"
        pid = f"pipeline:{relpath}:{fn.name}"
        nodes.extend([
            {"id": fid, "kind": model.FUNCTION, "name": fn.name,
             "summary": "pipeline composition function (Python)",
             "file": relpath, "line": fn.lineno},
            {"id": pid, "kind": model.PIPELINE, "name": fn.name,
             "summary": "Python composition pipeline", "file": relpath,
             "line": fn.lineno},
        ])
        edges.append({"src": pid, "dst": fid, "kind": model.PIPELINE_COMPOSED_BY,
                      "props": {"language": "python"}, "evidence": ev(fn)})

        stage_events, list_names = [], set()
        for assign in lists:
            names = [target.id for target in assign.targets if isinstance(target, ast.Name)]
            if not names:
                continue
            list_names.update(names)
            for item in assign.value.elts:
                target, kind = _stage_target(item)
                if target:
                    stage_events.append((getattr(item, "lineno", assign.lineno),
                                         getattr(item, "col_offset", assign.col_offset),
                                         target, kind, item, "python-list"))
        # ``for stage in pipeline: pm.add_pass(stage)`` consumes the list
        # declaration above; adding it again would fabricate a third stage.
        for loop in ast.walk(fn):
            if (isinstance(loop, ast.For) and isinstance(loop.iter, ast.Name) and
                    loop.iter.id in list_names and isinstance(loop.target, ast.Name)):
                list_names.add(loop.target.id)

        for call in calls:
            if not isinstance(call.func, ast.Attribute):
                name = _dotted(call.func)
                is_binding = name.startswith("make_")
                is_builder = name.startswith("build") and name.endswith("Pipeline")
                if (is_binding or is_builder) and any(_contains_pm(arg, pm_names)
                                                       for arg in call.args):
                    dst = (f"binding:NAME:{name}" if is_binding
                           else f"pipeline:NAME:{name}")
                    edges.append({"src": pid, "dst": dst,
                                  "kind": model.PIPELINE_CALLS,
                                  "props": {"language": "python",
                                            "via": "binding" if is_binding else "direct-builder"},
                                  "evidence": ev(call, model.INFERRED)})
                continue
            receiver, method = call.func.value, call.func.attr
            if (isinstance(receiver, ast.Name) and receiver.id in pm_names and
                    method in ("add_pass", "addPass", "add_nested_pass", "addNestedPass")):
                if not call.args or (isinstance(call.args[0], ast.Name) and
                                     call.args[0].id in list_names):
                    continue
                target, kind = _stage_target(call.args[0])
                if target:
                    stage_events.append((call.lineno, call.col_offset, target, kind,
                                         call, "pm-add"))
                continue
            if method.startswith("add_") and any(_contains_pm(arg, pm_names)
                                                   for arg in call.args):
                stage_events.append((call.lineno, call.col_offset,
                                     f"binding:NAME:{method}", "binding", call,
                                     "binding-add"))

        stage_events.sort(key=lambda item: (item[0], item[1]))
        previous = None
        for order, (_, _, target, kind, source, origin) in enumerate(stage_events, 1):
            props = {"order": order, "seq": order, "scope": "python",
                     "stage_kind": kind, "origin": origin, "pipeline": pid}
            edges.append({"src": pid, "dst": target, "kind": model.PIPELINE_CONTAINS,
                          "props": props, "evidence": ev(source)})
            if target.startswith("binding:NAME:"):
                edges.append({"src": fid, "dst": target, "kind": model.PYTHON_COMPOSES,
                              "props": {"stage_order": order}, "evidence": ev(source)})
            if previous:
                edges.append({"src": previous, "dst": target, "kind": model.PRECEDES,
                              "props": {"pipeline": pid, "scope": "python",
                                        "order": order}, "evidence": ev(source)})
            previous = target
    return {"nodes": nodes, "edges": edges, "diagnostics": []}
