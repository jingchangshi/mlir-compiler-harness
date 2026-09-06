"""Semantic finding impact analysis (Phase 16, ADR-022).

Deterministic join between a finding (doc layer), the graph (entities,
constraints, tests) and git history:

    changed compiler entity -> affected constraints -> affected finding
    -> review scope suggestion

Signals are structural (file commits, constraint added/removed/moved, test
coverage edges); the service never mutates finding state, never judges whether
a change fixed a bug, and never writes reasoning into the graph (ADR-019/020).
Uncertainty (unresolvable refs, missing baseline) is explicit.
"""

import os
from collections import Counter, defaultdict

from . import model
from .findings import FindingService, _git, _norm
from .extractors.cpppass import scan_constraints

ENTITY_REF_KINDS = ("pass", "pattern", "attribute", "op", "operation",
                    "pipeline", "function", "dialect")
_REF_KIND_MAP = {"operation": "op"}


def constraint_diff(repo, relpath, since):
    """Constraint-set diff for one file between a base commit and the worktree.

    Purely structural: added / removed / moved guards by (kind, normalized
    text). Classification labels are structural counts, never semantic
    judgments about whether a change is correct.
    """
    old_text = _git(repo, "show", f"{since}:{relpath}") if since else None
    abs_path = os.path.join(repo, relpath)
    if os.path.exists(abs_path):
        with open(abs_path, encoding="utf-8", errors="replace") as fh:
            new_text = fh.read()
    else:
        new_text = _git(repo, "show", f"HEAD:{relpath}")
    out = {"file": relpath, "since": since, "added": [], "removed": [],
           "moved": [], "unchanged": 0, "classification": "unchanged"}
    if old_text is None:
        out["classification"] = "no baseline content (file absent at base ref)"
        return out
    if new_text is None:
        out["classification"] = "file no longer present"
        return out

    def keyed(recs):
        lines = defaultdict(list)
        for _, kind, line, txt in recs:
            lines[(kind, _norm(txt))].append(line)
        return lines

    old_lines = keyed(scan_constraints(relpath, old_text))
    new_lines = keyed(scan_constraints(relpath, new_text))
    for key in sorted(set(new_lines) - set(old_lines),
                      key=lambda k: min(new_lines[k])):
        out["added"].append({"kind": key[0], "line": min(new_lines[key]),
                             "text": key[1][:140]})
    for key in sorted(set(old_lines) - set(new_lines),
                      key=lambda k: min(old_lines[k])):
        out["removed"].append({"kind": key[0], "line": min(old_lines[key]),
                               "text": key[1][:140]})
    for key in sorted(set(old_lines) & set(new_lines)):
        if set(old_lines[key]) != set(new_lines[key]):
            out["moved"].append({"kind": key[0], "from": min(old_lines[key]),
                                 "to": min(new_lines[key]), "text": key[1][:140]})
        else:
            out["unchanged"] += 1
    if out["removed"] and not out["added"]:
        out["classification"] = "possible weakening (guard(s) removed)"
    elif out["added"] and not out["removed"]:
        out["classification"] = "possible strengthening (guard(s) added)"
    elif out["added"] and out["removed"]:
        out["classification"] = "changed guard set"
    elif out["moved"]:
        out["classification"] = "guards moved (same guard set)"
    return out


class ImpactService:
    """finding-impact: entity-aware impact report for one finding."""

    def __init__(self, root, findings_dir=None, git_repo=None):
        self.root = root
        self.findings_dir = findings_dir or os.path.join(
            root, "docs", "compiler-architecture", "findings")
        self.git_repo = git_repo or root
        self._query_svc = None

    def _query(self):
        if self._query_svc is None:
            from .query import QueryService
            self._query_svc = QueryService(self.root)
        return self._query_svc

    def close(self):
        if self._query_svc is not None:
            self._query_svc.close()
            self._query_svc = None

    def _resolve_ref(self, kind, name):
        kind = _REF_KIND_MAP.get(kind, kind)
        q = self._query()
        nid = f"{kind}:{name}"
        node = q._node_or_none(nid)
        if node:
            return {"kind": kind, "id": nid, "node": node,
                    "resolution": "exact"}, []
        cands = [n for n in q.store.search_nodes(name) if n["kind"] == kind]
        if len(cands) == 1:
            return {"kind": kind, "id": cands[0]["id"], "node": cands[0],
                    "resolution": "unique-name"}, []
        ref = {"kind": kind, "id": None, "node": None, "resolution": None}
        if cands:
            ref["resolution"] = "ambiguous"
            return ref, [f"ambiguous {kind} reference {name!r}: "
                         f"{[c['id'] for c in cands]} — resolve manually"]
        ref["resolution"] = "not-found"
        return ref, [f"no {kind} entity found for reference {name!r} "
                     "(uncertainty, not a fact)"]

    def impact(self, finding_id, since=None):
        fs = FindingService(self.findings_dir, repo=self.git_repo)
        findings, diags = fs.load()
        target = next((f for f in findings
                       if str(f["data"].get("id", "")).lower() ==
                       str(finding_id).lower()), None)
        if not target:
            return {"error": "not found", "id": finding_id,
                    "diagnostics": diags}
        d = target["data"]
        out = {"finding": {"id": d.get("id"), "pass": d.get("pass"),
                           "status": d.get("status"),
                           "statement": d.get("statement"),
                           "file": target["file"]},
               "affected_entities": [], "changed_signals": [],
               "test_signal": [], "review_scope": {},
               "uncertainty": [], "diagnostics": list(diags)}

        # 1. entity-aware references (validated against the graph)
        affected = []
        refs = list(d.get("entity_refs") or [])
        if d.get("pass") and not any("pass" in r for r in refs):
            refs.append({"pass": str(d["pass"])})
        for item in refs:
            kind, name = list(item.items())[0]
            res, unc = self._resolve_ref(kind, str(name))
            out["affected_entities"].append(res)
            out["uncertainty"].extend(unc)
            if res["node"]:
                affected.append(res)

        # 2. file-level drift per evidence file (Phase 14 signal, per file)
        baseline = since or (d.get("review") or {}).get("baseline_commit")
        if not baseline:
            out["uncertainty"].append(
                "no baseline: finding has no review.baseline_commit and no "
                "--since was given — drift and constraint diff not computed")
        else:
            if _git(self.git_repo, "rev-parse", "--verify",
                    f"{baseline}^{{commit}}") is None:
                out["uncertainty"].append(
                    f"baseline commit not found in {self.git_repo}: {baseline}")
            else:
                seen_files = set()
                for ev in d.get("evidence", []):
                    path = ev.get("file")
                    if not path or path in seen_files:
                        continue
                    seen_files.add(path)
                    if ev.get("repo"):
                        out["uncertainty"].append(
                            f"external-repo evidence ({ev['repo']}): {path} "
                            "not drift-checked here")
                        continue
                    log = _git(self.git_repo, "log", "--format=%h%x1f%s",
                               f"{baseline}..HEAD", "--", path) or ""
                    commits = [{"sha": s, "subject": subj}
                               for s, subj in (ln.split("\x1f", 1)
                                               for ln in filter(None,
                                                                log.splitlines()))]
                    if commits:
                        out["changed_signals"].append(
                            {"type": "file-commits", "file": path,
                             "commits": commits[:10],
                             "total": len(commits)})
                        # 3. constraint evolution on changed files
                        diff = constraint_diff(self.git_repo, path, baseline)
                        if diff["classification"] != "unchanged":
                            out["changed_signals"].append(
                                {"type": "constraint-diff", **diff})

        # 4. test coverage signal for affected passes (deterministic edges)
        q = self._query()
        for a in affected:
            if a["kind"] != "pass":
                continue
            tests = q.get_tests(a["node"]["name"]).get("tests", [])
            for t in tests:
                out["test_signal"].append({
                    "pass": a["node"]["name"], "test": t.get("test"),
                    "via": t.get("kind"),
                    "confidence": t.get("confidence"),
                    "evidence": t.get("evidence")})

        # 5. review scope suggestion (deterministic composition, no judgment)
        areas = []
        for a in affected:
            area = {"entity": a["id"], "kind": a["kind"]}
            if a["kind"] == "pass":
                kinds = Counter(
                    e["props"].get("kind")
                    for e in q.store.edges_from(a["id"], model.HAS_CONSTRAINT))
                area["constraint_areas"] = dict(sorted(kinds.items()))
                area["constraints_total"] = sum(kinds.values())
            areas.append(area)
        if areas:
            names = ", ".join(a["entity"] for a in areas)
            parts = []
            for a in areas:
                if a.get("constraint_areas"):
                    parts.append(f"{a['entity']} (constraints: "
                                 f"{a['constraint_areas']}, "
                                 f"total {a['constraints_total']})")
                else:
                    parts.append(a["entity"])
            sug = ("Review " + "; ".join(parts))
            if out["test_signal"]:
                sug += (f"; {len(out['test_signal'])} linked test(s) to "
                        "re-run/inspect")
            if not out["changed_signals"]:
                sug += " (no file-level drift detected since baseline)"
            out["review_scope"] = {"areas": areas, "suggestion": sug}
        else:
            out["review_scope"] = {
                "areas": [],
                "suggestion": ("no resolvable affected entities — review the "
                               "finding's evidence manually")}
        if not out["changed_signals"] and not out["uncertainty"]:
            out["note"] = ("no impact signals since baseline "
                           "(files unchanged); negative result is a result")
        return out
