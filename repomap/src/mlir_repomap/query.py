"""QueryService: the single implementation of the stable query contract (query-api.md).

CLI / MCP / Python frontends must contain no business logic, only this module.
"""
import json
import os

from . import model, repo
from .store import Store


class QueryService:
    def __init__(self, root):
        self.root = root
        self.store = Store(root)

    def close(self):
        self.store.close()

    # ---- helpers ----
    def _index_info(self):
        meta = self.store.get_meta("last_build", {}) or {}
        facts = repo.git_facts(self.root)
        worktree_snapshot = repo.worktree_snapshot(self.root)
        stale = (not meta) or meta.get("head") != facts.get("head") or (
            meta.get("worktree_snapshot") != worktree_snapshot)
        return {"head": meta.get("head"), "branch": meta.get("branch"),
                "indexed_at": meta.get("when"), "schema_version": meta.get("schema_version"),
                "current_head": facts.get("head"), "current_branch": facts.get("branch"),
                "stale": bool(stale)}

    def _node_or_none(self, nid):
        return self.store.node(nid)

    def _evidence_summary(self, edges):
        for e in edges:
            e["confidence"] = (max((x["confidence"] for x in e["evidence"]),
                                   key=["heuristic", "inferred", "exact", "confirmed"].index)
                               if e["evidence"] else "unknown")
        return edges

    # ---- contract commands ----
    def repo_status(self):
        counts = self.store.counts()
        diags = self.store.db.execute("SELECT COUNT(*) FROM diagnostics").fetchone()[0]
        meta = self.store.get_meta("last_build", {}) or {}
        return {"index": self._index_info(), "entity_counts": counts,
                "diagnostics": diags, "last_build_stats": meta.get("stats")}

    def modules(self, depth=2):
        """Major directory modules by entity density. depth=1 for top-level dirs."""
        db = self.store.db
        rows = db.execute("SELECT file FROM nodes WHERE file != ''").fetchall()
        agg = {}
        for (f,) in rows:
            comps = f.split("/")
            key = "/".join(comps[:max(1, min(depth, len(comps)))])
            agg[key] = agg.get(key, 0) + 1
        out = sorted(({"module": k, "entities": v} for k, v in agg.items()),
                     key=lambda x: -x["entities"])
        return {"modules": out[:40]}

    def dialects(self, name=None):
        ds = self.store.nodes_by_kind(model.DIALECT)
        out = []
        for d in ds:
            if name and name.lower() not in d["name"].lower():
                continue
            own = self.store.edges_from(d["id"], model.DIALECT_OWNS)
            by_kind = {}
            for e in own:
                k = e["dst"].split(":", 1)[0]
                by_kind[k] = by_kind.get(k, 0) + 1
            out.append({**{k: d[k] for k in ("id", "name", "summary", "file", "line")},
                        "owns": by_kind})
        return {"dialects": out}

    def passes(self, query=None):
        ps = self.store.nodes_by_kind(model.PASS)
        if query:
            ps = [p for p in ps if query.lower() in p["name"].lower()]
        return {"passes": [{k: p[k] for k in ("id", "name", "summary", "file", "line")}
                           for p in ps]}

    def _resolve_pass(self, name):
        """Resolve a pass by arg, td class, cpp class, or factory name.

        Multiple strategies vote; a unique candidate resolves, several candidates
        return an explicit ambiguity error (never a silent pick).
        """
        nid = name if name.startswith("pass:") else f"pass:{name}"
        node = self._node_or_none(nid)
        if node:
            return nid, node
        cands = set()
        rows = self.store.db.execute(
            "SELECT id FROM nodes WHERE kind='pass' AND LOWER(name)=LOWER(?)",
            (name,)).fetchall()
        cands |= {r[0] for r in rows}
        for cls in (name, name + "Pass"):
            rows = self.store.db.execute(
                "SELECT props FROM edges WHERE kind='DEFINES'").fetchall()
            for (p,) in rows:
                props = json.loads(p)
                if cls in (props.get("tblgen_class"), props.get("cpp_class")):
                    rows2 = self.store.db.execute(
                        "SELECT dst FROM edges WHERE kind='DEFINES' AND props=?",
                        (p,)).fetchall()
                    for (d,) in rows2:
                        if d.startswith("pass:"):
                            cands.add(d)
        fac = name if name.startswith("create") else f"create{name}Pass"
        rows = self.store.db.execute(
            "SELECT src FROM edges WHERE kind='PASS_HAS_FACTORY' AND dst=?",
            (f"factory:{fac}",)).fetchall()
        cands |= {r[0] for r in rows}
        if len(cands) == 1:
            nid = next(iter(cands))
            return nid, self._node_or_none(nid)
        if len(cands) > 1:
            return None, {"error": "ambiguous", "candidates": sorted(cands)}
        cands = {n["id"] for n in self.store.search_nodes(name)
                 if n["kind"] == model.PASS}
        if len(cands) == 1:
            nid = next(iter(cands))
            return nid, self._node_or_none(nid)
        if cands:
            return None, {"error": "ambiguous", "candidates": sorted(cands)}
        return None, {"error": "not found"}

    def get_pass(self, name):
        nid, node = self._resolve_pass(name)
        if node is None or "error" in node:
            return node if isinstance(node, dict) else {"error": "not found"}
        memberships = []
        for e in self._evidence_summary(self.store.edges_to(nid, model.PIPELINE_CONTAINS)):
            memberships.append({"pipeline": e["src"], "scope": e["props"].get("scope"),
                                "order": e["props"].get("order"),
                                "condition": e["props"].get("condition"),
                                "disambiguation": e["props"].get("disambiguation"),
                                "confidence": e["confidence"],
                                "evidence": e["evidence"]})
        for m in memberships:
            # predecessor / successor via PRECEDES within the same pipeline+scope
            def same_ctx(props):
                return (props.get("pipeline") in m["pipeline"]
                        and props.get("scope") == m["scope"])
            pe = self.store.edges_from(nid, model.PRECEDES)
            m["successor"] = [e["dst"] for e in pe if same_ctx(e["props"])]
            se = self.store.edges_to(nid, model.PRECEDES)
            m["predecessor"] = [e["src"] for e in se if same_ctx(e["props"])]
        patterns = []
        seen_patterns = set()
        for e in self.store.edges_from(nid, model.PASS_USES_PATTERN):
            pat = e["dst"]
            seen_patterns.add(pat)
            p = self._node_or_none(pat) or {"id": pat}
            matches = [x["dst"] for x in self.store.edges_from(pat, model.PATTERN_MATCHES_OP)]
            creates = [x["dst"] for x in self.store.edges_from(pat, model.PATTERN_CREATES_OP)]
            patterns.append({"pattern": pat, "node": p, "matches_ops": matches,
                             "creates_ops": creates, "evidence": e["evidence"]})
        # provenance chain (ADR-012): pass -> populator function -> patterns
        for e in self._evidence_summary(
                self.store.edges_from(nid, model.PASS_USES_PATTERN_POPULATOR)):
            fid = e["dst"]
            fn = self._node_or_none(fid) or {"id": fid}
            pats = [x["dst"] for x in self.store.edges_from(fid, model.FUNCTION_DEFINES_PATTERN)
                    if x["dst"] not in seen_patterns]
            seen_patterns.update(pats)
            pat_detail = []
            for pat in pats:
                pat_detail.append({
                    "pattern": pat,
                    "matches_ops": [x["dst"] for x in self.store.edges_from(
                        pat, model.PATTERN_MATCHES_OP)],
                    "creates_ops": [x["dst"] for x in self.store.edges_from(
                        pat, model.PATTERN_CREATES_OP)]})
            patterns.append({"populator": fid, "node": fn, "confidence": e["confidence"],
                             "evidence": e["evidence"], "patterns": pat_detail})
            # nested pattern-set helpers, recursively (populate -> helper -> pattern)
            def walk_functions(f, depth, seen):
                if depth > 4 or f in seen:
                    return
                seen.add(f)
                for ce in self.store.edges_from(f, model.FUNCTION_CALLS):
                    sub_id = ce["dst"]
                    sub = self._node_or_none(sub_id) or {"id": sub_id}
                    sub_pats = [x["dst"] for x in self.store.edges_from(
                        sub_id, model.FUNCTION_DEFINES_PATTERN)
                        if x["dst"] not in seen_patterns]
                    seen_patterns.update(sub_pats)
                    if sub_pats:
                        patterns.append({"populator": sub_id, "node": sub,
                                         "confidence": "inferred",
                                         "evidence": ce["evidence"],
                                         "patterns": [{"pattern": pt,
                                                       "matches_ops": [x["dst"] for x in
                                                                       self.store.edges_from(pt, model.PATTERN_MATCHES_OP)],
                                                       "creates_ops": []} for pt in sub_pats]})
                    walk_functions(sub_id, depth + 1, seen)
            walk_functions(fid, 0, set())
        factories = [e["dst"] for e in self.store.edges_from(nid, model.PASS_HAS_FACTORY)]
        impl = [e["dst"] for e in self.store.edges_from(nid, model.PASS_IMPLEMENTS)]
        tests = self.get_tests(node["name"]).get("tests", [])
        return {"pass": node,
                "definition": [e for e in self.store.edges_to(nid, model.DEFINES)],
                "factory": factories, "registration": impl,
                "pipeline_memberships": memberships,
                "patterns": patterns, "analyses": [],
                "tests": tests, "diagnostics": []}

    def pipelines(self):
        ps = self.store.nodes_by_kind(model.PIPELINE)
        out = []
        for p in ps:
            n = len(self.store.edges_from(p["id"], model.PIPELINE_CONTAINS))
            out.append({k: p[k] for k in ("id", "name", "file", "line")} | {"stages": n})
        out.sort(key=lambda x: -x["stages"])
        return {"pipelines": out}

    def get_pipeline(self, name, brief=False):
        node = None
        if name.startswith("pipeline:"):
            node = self._node_or_none(name)
            nid = name
            if node is None:
                # fall through to name-based resolution on the bare name
                name = name.rsplit(":", 1)[-1]
        else:
            exact = [p for p in self.store.nodes_by_kind(model.PIPELINE)
                     if p["name"] == name]
            if len(exact) == 1:
                nid, node = exact[0]["id"], exact[0]
            elif exact:
                return {"error": "ambiguous", "candidates": [p["id"] for p in exact]}
            else:
                cands = [n for n in self.store.search_nodes(name)
                         if n["kind"] == model.PIPELINE]
                if len(cands) == 1:
                    nid, node = cands[0]["id"], cands[0]
                elif cands:
                    return {"error": "ambiguous", "candidates": [c["id"] for c in cands]}
                else:
                    return {"error": "not found"}
            if node is None:
                return {"error": "not found"}
        stages = []
        for e in self._evidence_summary(self.store.edges_from(nid, model.PIPELINE_CONTAINS)):
            stage = {"pass": e["dst"], "order": e["props"].get("order"),
                     "seq": e["props"].get("seq"),
                     "scope": e["props"].get("scope"),
                     "nested": e["props"].get("nested", False),
                     "condition": e["props"].get("condition"),
                     "confidence": e["confidence"]}
            if not brief:
                stage["evidence"] = e["evidence"]
            stages.append(stage)
        stages.sort(key=lambda s: (s.get("seq") if s.get("seq") is not None
                                   else s["order"] or 0,))
        subs = [e["dst"] for e in self.store.edges_from(nid, model.PIPELINE_CALLS)]
        callers = [e["src"] for e in self.store.edges_to(nid, model.PIPELINE_CALLS)]
        tests = self.get_tests(node["name"]).get("tests", [])
        return {"pipeline": node, "stages": stages, "sub_pipelines": subs,
                "called_by": callers, "tests": tests}

    def find_symbol(self, name):
        return {"symbols": self.store.search_nodes(name)}

    def get_references(self, name):
        nid = name if ":" in name else None
        if not nid:
            cands = self.store.search_nodes(name)
            exact = [c for c in cands if c["name"] == name]
            if exact:
                nid = exact[0]["id"]
            elif cands:
                return {"error": "ambiguous", "candidates": [c["id"] for c in cands[:20]]}
            else:
                return {"error": "not found"}
        return {"id": nid,
                "outgoing": self._evidence_summary(self.store.edges_from(nid)),
                "incoming": self._evidence_summary(self.store.edges_to(nid))}

    def get_tests(self, name):
        nid = name if name.startswith(("pass:", "pipeline:")) else None
        if not nid:
            n = self.store.search_nodes(name)
            exact = [c for c in n if c["name"] == name]
            nid = exact[0]["id"] if exact else (n[0]["id"] if len(n) == 1 else None)
        if not nid:
            return {"tests": []}
        tests = []
        for e in self._evidence_summary(
                self.store.edges_to(nid, model.TEST_COVERS_PASS)
                + self.store.edges_to(nid, model.TEST_EXERCISES_PIPELINE)):
            node = self._node_or_none(e["src"]) or {}
            tests.append({"test": e["src"], "kind": e["kind"],
                          "confidence": e["confidence"], "evidence": e["evidence"],
                          "features": (node.get("summary") or "")
                          .replace("features: ", "").split(",")
                          if (node.get("summary") or "").startswith("features: ") else []})
        return {"tests": tests}

    def get_changes(self, base=None):
        dirty = repo.changed_vs_head(self.root)
        changed = []
        if base:
            changed = repo.diff_vs_base(self.root, base) or []
        else:
            if dirty:
                changed = (dirty["added"] + dirty["modified"] + dirty["renamed"] +
                           [d["to"] for d in dirty.get("renamed", [])])
        impacted = set()
        for f in changed:
            for r in self.store.db.execute(
                    "SELECT id FROM nodes WHERE file=?", (f,)):
                impacted.add(r[0])
            for r in self.store.db.execute(
                    "SELECT DISTINCT edge_id FROM evidence WHERE file=?", (f,)):
                er = self.store.db.execute("SELECT src,dst FROM edges WHERE edge_id=?",
                                           r).fetchone()
                if er:
                    impacted.update(er)
        return {"index": self._index_info(), "changed_files": sorted(set(changed)),
                "dirty_detail": dirty, "impacted_entities": sorted(impacted)[:200]}

    def pattern_owner(self, name):
        """Provenance chain: pattern -> defining populator function(s) -> pass(es)."""
        pat = name if name.startswith("pattern:") else f"pattern:{name}"
        node = self._node_or_none(pat)
        if not node:
            cands = [n for n in self.store.search_nodes(name) if n["kind"] == model.PATTERN]
            if len(cands) == 1:
                pat, node = cands[0]["id"], cands[0]
            elif cands:
                return {"error": "ambiguous", "candidates": [c["id"] for c in cands]}
            else:
                return {"error": "not found"}
        owners = []
        for e in self._evidence_summary(
                self.store.edges_to(pat, model.FUNCTION_DEFINES_PATTERN)):
            fid = e["src"]
            fn = self._node_or_none(fid) or {"id": fid}
            # walk the call chain upward: passes use this function directly or via helpers
            passes, called_by, seen = [], [], set()

            def walk_up(f):
                if f in seen:
                    return
                seen.add(f)
                for x in self.store.edges_to(f, model.PASS_USES_PATTERN_POPULATOR):
                    passes.append({"src": x["src"], "evidence": x["evidence"]})
                for x in self.store.edges_to(f, model.FUNCTION_CALLS):
                    called_by.append(x["src"])
                    walk_up(x["src"])

            walk_up(fid)
            owners.append({"function": fid, "node": fn, "evidence": e["evidence"],
                           "passes": passes, "called_by": called_by})
        direct = self._evidence_summary(self.store.edges_to(pat, model.PASS_USES_PATTERN))
        return {"pattern": node, "populators": owners,
                "direct_uses": [{"src": e["src"], "evidence": e["evidence"]}
                                for e in direct]}

    def pipeline_builder(self, name):
        """Builder function(s) of a pipeline (file-qualified identity, QG-1)."""
        r = self.get_pipeline(name, brief=True)
        if "error" in r:
            return r
        pid = r["pipeline"]["id"]
        builders = self._evidence_summary(
            self.store.edges_from(pid, model.PIPELINE_BUILT_BY))
        subs = self._evidence_summary(self.store.edges_from(pid, model.PIPELINE_CALLS))
        callers = self._evidence_summary(self.store.edges_to(pid, model.PIPELINE_CALLS))
        return {"pipeline": r["pipeline"], "builders": builders,
                "calls": subs, "called_by": callers}

    def get_attribute(self, name):
        """Attribute provenance: who references/creates an IR attribute."""
        aid = name if name.startswith("attribute:") else f"attribute:{name}"
        node = self._node_or_none(aid)
        if not node:
            cands = [n for n in self.store.search_nodes(name) if n["kind"] == model.ATTRIBUTE]
            if len(cands) == 1:
                aid, node = cands[0]["id"], cands[0]
            elif cands:
                return {"error": "ambiguous", "candidates": [c["id"] for c in cands]}
            else:
                return {"error": "not found"}
        refs = self._evidence_summary(self.store.edges_to(aid, model.REFERENCES))
        creates = self._evidence_summary(self.store.edges_to(aid, model.CREATES_ATTRIBUTE))
        return {"attribute": node, "referenced_by": refs, "created_by": creates}

    def attribute_provenance(self, name):
        """Typed creator provenance for an IR attribute (Phase 15 / RG-1).

        Deterministic join of: td definition (attr:<Name> + DIALECT_OWNS), typed
        creators (CREATES_ATTRIBUTE with creator_type), and typed consumers
        (REFERENCES with role, from containers rather than bare files).
        Ambiguity is explicit; nothing is guessed.
        """
        aid = name if name.startswith("attribute:") else f"attribute:{name}"
        node = self._node_or_none(aid)
        if not node:
            cands = [n for n in self.store.search_nodes(name)
                     if n["kind"] == model.ATTRIBUTE]
            if len(cands) == 1:
                aid, node = cands[0]["id"], cands[0]
            elif cands:
                return {"error": "ambiguous", "candidates": [c["id"] for c in cands]}
            else:
                # definition-only attribute: a td AttrDef exists without IR refs
                anode = self._node_or_none(f"attr:{name}")
                if anode:
                    out = {"attribute": anode, "definitions": [],
                           "creators": [], "consumers": [],
                           "referenced_by_files": [],
                           "diagnostics": ["no IR-level references found "
                                           "(definition-only attribute)"]}
                    owners = [{"dialect": e["src"], "evidence": e["evidence"]}
                              for e in self._evidence_summary(
                                  self.store.edges_to(anode["id"],
                                                      model.DIALECT_OWNS))]
                    out["definitions"].append({"node": anode, "dialects": owners,
                                               "confidence": "confirmed"})
                    return out
                return {"error": "not found"}
        out = {"attribute": node, "definitions": [], "creators": [],
               "consumers": [], "referenced_by_files": [], "diagnostics": []}
        # td definition side: exact-name AttrDef + its owning dialect
        anode = self._node_or_none(f"attr:{node['name']}")
        if anode:
            owners = [{"dialect": e["src"], "evidence": e["evidence"]}
                      for e in self._evidence_summary(
                          self.store.edges_to(anode["id"], model.DIALECT_OWNS))]
            out["definitions"].append({"node": anode, "dialects": owners,
                                       "confidence": "confirmed"})
        # creators: typed CREATES_ATTRIBUTE
        for e in self._evidence_summary(
                self.store.edges_to(aid, model.CREATES_ATTRIBUTE)):
            out["creators"].append({
                "entity": self._node_or_none(e["src"]) or {"id": e["src"]},
                "type": e["props"].get("creator_type"),
                "attach": e["props"].get("attach", False),
                "confidence": e["confidence"], "evidence": e["evidence"]})
        # consumers: container-level references with a role
        for e in self.store.edges_to(aid, model.REFERENCES):
            if e["src"].startswith("file:"):
                out["referenced_by_files"].append(
                    {"file": e["src"][len("file:"):], "evidence": e["evidence"]})
            else:
                out["consumers"].append({
                    "entity": self._node_or_none(e["src"]) or {"id": e["src"]},
                    "role": e["props"].get("role"),
                    "evidence": e["evidence"]})
        if not out["definitions"]:
            out["diagnostics"].append(
                "no TableGen AttrDef definition found (name-level reference only)")
        if not out["creators"]:
            out["diagnostics"].append(
                "no typed creator found — references are file-level only")
        return out

    def pipeline_composition(self, name):
        """Cross-language construction chain for a pass (Phase 9):
        Python composition function -> binding -> C++ factory -> pass."""
        r = self._resolve_pass(name)
        if r is None or (isinstance(r[1], dict) and "error" in r[1]):
            return r[1] if isinstance(r[1], dict) else {"error": "not found"}
        nid, node = r
        out = {"pass": node, "composition": []}
        for e in self._evidence_summary(
                self.store.edges_to(nid, model.BINDING_EXPOSES_PASS)):
            bind = e["src"]
            bnode = self._node_or_none(bind) or {"id": bind}
            composers = [x["src"] for x in self.store.edges_to(bind, model.PYTHON_COMPOSES)]
            maps = self.store.edges_from(bind, model.BINDING_MAPS_TO)
            out["composition"].append({
                "binding": bind, "node": bnode, "confidence": e["confidence"],
                "evidence": e["evidence"],
                "maps_to": [{"dst": m["dst"], "evidence": m["evidence"]}
                            for m in maps],
                "python_composers": composers})
        # direct td-constructor path (no binding) for contrast
        out["direct_factory"] = [e["dst"] for e in
                                 self.store.edges_from(nid, model.PASS_HAS_FACTORY)]
        return out

    def dialect_transition(self, name):
        """Dialect transitions of a pass (Phase 10): input/output dialects with
        evidence, plus derived dialect->dialect pairs."""
        r = self._resolve_pass(name)
        if r is None or (isinstance(r[1], dict) and "error" in r[1]):
            return r[1] if isinstance(r[1], dict) else {"error": "not found"}
        nid, node = r
        ins, outs = [], []
        for e in self._evidence_summary(
                self.store.edges_from(nid, model.DIALECT_TRANSITIONS_TO)):
            d = self._node_or_none(e["dst"]) or {"id": e["dst"]}
            entry = {"dialect": e["dst"], "node": d, "role": e["props"].get("role"),
                     "via": e["props"].get("via"), "confidence": e["confidence"],
                     "evidence": e["evidence"]}
            (outs if e["props"].get("role") == "output" else ins).append(entry)
        pairs = [{"from": i["dialect"], "to": o["dialect"]}
                 for i in ins for o in outs]
        return {"pass": node, "input_dialects": ins, "output_dialects": outs,
                "transitions": pairs}

    def semantic_contract(self, name):
        """Attribute semantic contract: role + producers + consumers."""
        r = self.get_attribute(name)
        if "error" in r:
            return r
        node = r["attribute"]
        role = (node.get("summary") or "").replace("role: ", "").replace(" (heuristic)", "")
        return {"attribute": node,
                "role": role or "unknown",
                "producers": r["created_by"],
                "consumers": r["referenced_by"]}

    def boundary(self, name):
        """IR boundary contract of a pass: why this is a lowering boundary."""
        r = self.dialect_transition(name)
        if "error" in r:
            return r
        created = set()
        for e in self.store.edges_from(r["pass"]["id"], model.PASS_USES_PATTERN):
            for c in self.store.edges_from(e["dst"], model.PATTERN_CREATES_OP):
                created.add(c["dst"])
        for c in r["composition"] if "composition" in r else []:
            pass
        succ = set()
        for m in self.get_pass(name).get("pipeline_memberships", []):
            succ.update(m.get("successor") or [])
        return {"pass": r["pass"],
                "input_dialects": r["input_dialects"],
                "output_dialects": r["output_dialects"],
                "transitions": r["transitions"],
                "created_ops": sorted(created),
                "downstream_assumptions": sorted(succ)}

    def pass_constraints(self, name):
        r = self._resolve_pass(name)
        if r is None or (isinstance(r[1], dict) and "error" in r[1]):
            return r[1] if isinstance(r[1], dict) else {"error": "not found"}
        nid, node = r
        out = []
        for e in self._evidence_summary(
                self.store.edges_from(nid, model.HAS_CONSTRAINT)):
            c = self._node_or_none(e["dst"]) or {"id": e["dst"]}
            out.append({"constraint": e["dst"], "kind": e["props"].get("kind"),
                        "text": c.get("summary"), "confidence": e["confidence"],
                        "evidence": e["evidence"]})
        by_kind = {}
        for c in out:
            by_kind[c["kind"]] = by_kind.get(c["kind"], 0) + 1
        return {"pass": node, "constraints": out, "counts": by_kind}

    def pass_intent(self, name):
        """Layered compiler intent: graph facts only; agent interpretation lives in
        the dossier layer and is deliberately absent here (ADR-018)."""
        r = self._resolve_pass(name)
        if r is None or (isinstance(r[1], dict) and "error" in r[1]):
            return r[1] if isinstance(r[1], dict) else {"error": "not found"}
        nid, node = r
        b = self.boundary(name)
        ins = [d["dialect"] for d in b.get("input_dialects", [])]
        outs = [d["dialect"] for d in b.get("output_dialects", [])]
        cons = self.pass_constraints(name)
        comp = self.pipeline_composition(name)
        n_patterns = len(self.get_pass(name).get("patterns", []))
        # deterministic intent label: graph facts first, name/summary keywords as
        # heuristic fallback (never presented as confirmed)
        blob = ((node.get("summary") or "") + " " + name).lower()
        if outs:
            label, conf = "lowering/conversion boundary", "inferred"
        elif n_patterns:
            label, conf = "in-place rewrite/optimization", "inferred"
        elif any(k in blob for k in ("vectorize", "fuse", "merge", "optimize",
                                     "simplify", "canonicaliz", "fold", "hoist",
                                     "pipeline", "tile", "unroll")):
            label, conf = "optimization pass (name/summary heuristic)", "heuristic"
        elif any(m.get("nested") for m in self.get_pass(name).get("pipeline_memberships", [])):
            label, conf = "structural/scheduling pass", "heuristic"
        else:
            label, conf = "structural pass", "heuristic"
        return {"pass": node,
                "stated_intent": node.get("summary"),
                "intent_label": {"label": label, "confidence": conf},
                "evidence": {"input_dialects": ins, "output_dialects": outs,
                             "pattern_count": n_patterns,
                             "composition_chains": len(comp.get("composition", []))
                             if isinstance(comp, dict) else 0},
                "constraints": {"counts": cons.get("counts", {}),
                                "items": cons.get("constraints", [])[:12]}}

    def get_evidence(self, ident):
        """Evidence catalog (Phase 17): entity + evidence rows + findings that
        reference it + recent git history of its location. Structural matching
        only — no embedding, no similarity."""
        if ident.startswith("file:"):
            return {"evidence": []}
        node = self._node_or_none(ident)
        out = []
        if node:
            out += self._evidence_summary(self.store.edges_from(ident))
            out += self._evidence_summary(self.store.edges_to(ident))
        else:
            out = []
        diags = self.store.db.execute(
            "SELECT message FROM diagnostics WHERE file=?",
            (ident[5:] if ident.startswith("file:") else "",)).fetchall()
        result = {"id": ident, "entity": node, "evidence_rows": out,
                  "referenced_by_findings": [], "recent_history": [],
                  "diagnostics": [d[0] for d in diags]}
        # evidence-point catalog: findings referencing this entity (Phase 17)
        if node:
            fdir = os.path.join(self.root, "docs", "compiler-architecture",
                                "findings")
            try:
                from .findings import FindingService
                findings, _ = FindingService(fdir, repo=self.root).load()
            except Exception:
                findings = []
            for f in findings:
                d = f["data"]
                via = []
                for ev in d.get("evidence", []):
                    if ev.get("ref") == ident:
                        via.append("evidence.ref")
                    elif node.get("file") and ev.get("file") == node.get("file"):
                        via.append("evidence.file")
                for item in d.get("entity_refs") or []:
                    kind, name = list(item.items())[0]
                    if ident == f"{kind}:{name}" or name == node.get("name"):
                        via.append("entity_refs")
                if via:
                    result["referenced_by_findings"].append(
                        {"id": d.get("id"), "status": d.get("status"),
                         "file": f["file"], "matched_via": sorted(set(via))})
            # recent history: commits touching the entity's primary file
            if node.get("file"):
                from .repo import _git
                log = _git(self.root, "log", "--format=%h%x1f%ad%x1f%s",
                           "--date=short", "-5", "--", node["file"]) or ""
                result["recent_history"] = [
                    {"sha": s, "date": dt, "subject": subj}
                    for s, dt, subj in (ln.split("\x1f", 2)
                                        for ln in filter(None,
                                                         log.splitlines()))]
        return result
