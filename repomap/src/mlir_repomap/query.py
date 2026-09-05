"""QueryService: the single implementation of the stable query contract (query-api.md).

CLI / MCP / Python frontends must contain no business logic, only this module.
"""
import json

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
        dirty = repo.changed_vs_head(self.root)
        stale = (not meta) or meta.get("head") != facts.get("head") or (
            dirty and (dirty.get("modified") or dirty.get("added") or dirty.get("deleted")))
        return {"head": meta.get("head"), "branch": meta.get("branch"),
                "indexed_at": meta.get("when"), "schema_version": meta.get("schema_version"),
                "current_head": facts.get("head"), "current_branch": facts.get("branch"),
                "stale": bool(stale)}

    def _node_or_none(self, nid):
        return self.store.node(nid)

    def _evidence_summary(self, edges):
        for e in edges:
            e["confidence"] = (max((x["confidence"] for x in e["evidence"]),
                                   key=["heuristic", "inferred", "confirmed"].index)
                               if e["evidence"] else "unknown")
        return edges

    # ---- contract commands ----
    def repo_status(self):
        counts = self.store.counts()
        diags = self.store.db.execute("SELECT COUNT(*) FROM diagnostics").fetchone()[0]
        meta = self.store.get_meta("last_build", {}) or {}
        return {"index": self._index_info(), "entity_counts": counts,
                "diagnostics": diags, "last_build_stats": meta.get("stats")}

    def modules(self):
        db = self.store.db
        rows = db.execute(
            "SELECT substr(file,1,instr(file||'/','/')-1) AS top, COUNT(*) FROM nodes "
            "WHERE file != '' GROUP BY top ORDER BY 2 DESC LIMIT 30").fetchall()
        return {"modules": [{"top_dir": r[0], "entities": r[1]} for r in rows]}

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

    def get_pass(self, name):
        nid = name if name.startswith("pass:") else f"pass:{name}"
        node = self._node_or_none(nid)
        if not node:
            # fuzzy: unique substring match
            cands = [n for n in self.store.search_nodes(name) if n["kind"] == model.PASS]
            if len(cands) == 1:
                nid, node = cands[0]["id"], cands[0]
            elif cands:
                return {"error": "ambiguous", "candidates": [c["id"] for c in cands]}
            else:
                return {"error": "not found"}
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
        for e in self.store.edges_from(nid, model.PASS_USES_PATTERN):
            pat = e["dst"]
            p = self._node_or_none(pat) or {"id": pat}
            matches = [x["dst"] for x in self.store.edges_from(pat, model.PATTERN_MATCHES_OP)]
            creates = [x["dst"] for x in self.store.edges_from(pat, model.PATTERN_CREATES_OP)]
            patterns.append({"pattern": pat, "node": p, "matches_ops": matches,
                             "creates_ops": creates, "evidence": e["evidence"]})
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

    def get_pipeline(self, name):
        nid = name if name.startswith("pipeline:") else f"pipeline:{name}"
        node = self._node_or_none(nid)
        if not node:
            cands = [n for n in self.store.search_nodes(name) if n["kind"] == model.PIPELINE]
            if len(cands) == 1:
                nid, node = cands[0]["id"], cands[0]
            elif cands:
                return {"error": "ambiguous", "candidates": [c["id"] for c in cands]}
            else:
                return {"error": "not found"}
        stages = []
        for e in self._evidence_summary(self.store.edges_from(nid, model.PIPELINE_CONTAINS)):
            stages.append({"pass": e["dst"], "order": e["props"].get("order"),
                           "scope": e["props"].get("scope"),
                           "nested": e["props"].get("nested", False),
                           "condition": e["props"].get("condition"),
                           "confidence": e["confidence"], "evidence": e["evidence"]})
        stages.sort(key=lambda s: (s["scope"] or "", s["order"] or 0))
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
            tests.append({"test": e["src"], "kind": e["kind"],
                          "confidence": e["confidence"], "evidence": e["evidence"]})
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

    def get_evidence(self, ident):
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
        return {"id": ident, "edges": out, "diagnostics": [d[0] for d in diags]}
