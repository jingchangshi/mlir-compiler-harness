"""Ecosystem layer: cross-repository compiler handoff detection (Phase 11).

Reads N per-repo indexes (each produced by the normal RepoMap engine) and derives
HANDOFF relationships between repositories by matching compiler artifacts by name:

- dialect handoff: repo B's passes legalize (ConversionTarget) or create ops of a
  dialect that is *defined* in repo A -> "A defines the dialect, B consumes it".
- operation handoff: repo B's rewrite patterns create an op that is *defined and
  owned* in repo A (e.g. a conversion to another stack's op set).
- attribute contract: an attribute name referenced/created in both repositories.

No repository names are embedded in the engine: repo identity is the index path
(display name = basename). Everything is computed from the per-repo graphs; the
ecosystem layer owns no extraction logic.
"""
import os

from .store import Store
from . import model


class EcosystemQueryService:
    def __init__(self, repo_paths):
        self.repos = []  # (display_name, Store)
        for p in repo_paths:
            self.repos.append((os.path.basename(os.path.abspath(p)), Store(p)))
        self._dialect_defs = None  # name -> [(repo, node)]
        self._op_defs = None

    def close(self):
        for _, s in self.repos:
            s.close()

    # ---- helpers ----
    def _dialect_definitions(self):
        if self._dialect_defs is None:
            self._dialect_defs = {}
            for repo, s in self.repos:
                for d in s.nodes_by_kind(model.DIALECT):
                    self._dialect_defs.setdefault(d["name"], []).append((repo, d))
        return self._dialect_defs

    def _op_definitions(self):
        if self._op_defs is None:
            self._op_defs = {}
            for repo, s in self.repos:
                for o in s.nodes_by_kind(model.OP):
                    # index by both the id suffix (TableGen class, e.g. MarkOp)
                    # and the mnemonic name (e.g. mark) — references may use either
                    for key in {o["id"].split(":", 1)[-1], o["name"]}:
                        self._op_defs.setdefault(key, []).append((repo, o))
        return self._op_defs

    def _owning_dialect(self, repo, op_name):
        s = dict(self.repos)[repo]
        for e in s.edges_to(f"op:{op_name}", model.DIALECT_OWNS):
            return e["src"]
        return None

    # ---- handoff computation ----
    def dialect_handoffs(self, name=None):
        out = []
        defs = self._dialect_definitions()
        multi = {n for n, lst in defs.items() if len({r for r, _ in lst}) > 1}
        for repo, s in self.repos:
            for e in s.db.execute(
                    "SELECT edge_id, src, dst, props FROM edges "
                    "WHERE kind='DIALECT_TRANSITIONS_TO' AND dst LIKE 'dialect:%'"):
                dname = e[2].split(":", 1)[-1]
                if name and dname != name:
                    continue
                # who defines this dialect? any *other* repo (or same-repo td for
                # upstream dialects is not a handoff)
                producers = [(r, d) for r, d in defs.get(dname, []) if r != repo]
                if not producers:
                    continue
                ev = s.db.execute(
                    "SELECT file,line_start,confidence FROM evidence WHERE edge_id=? "
                    "LIMIT 1", (e[0],)).fetchone()
                out.append({"consumer": repo, "producer": producers[0][0],
                            "artifact": f"dialect:{dname}",
                            "consumer_pass": e[1],
                            "role": __import__("json").loads(e[3]).get("role"),
                            "confidence": (ev[2] if ev else "unknown"),
                            "evidence": {"file": ev[0], "line": ev[1]} if ev else None})
        return out

    def op_handoffs(self, name=None):
        out = []
        defs = self._op_definitions()
        for repo, s in self.repos:
            for e in s.db.execute(
                    "SELECT edge_id, src, dst FROM edges "
                    "WHERE kind='PATTERN_CREATES_OP'"):
                oname = e[2].split(":", 1)[-1]
                if name and oname != name:
                    continue
                producers = [(r, o) for r, o in defs.get(oname, []) if r != repo]
                if not producers:
                    continue
                # the created op must belong to the producer repo's dialect
                prod_repo, prod_node = producers[0]
                own_dialect = self._owning_dialect(prod_repo, oname)
                if not own_dialect:
                    continue
                # which pass created it?
                pass_row = s.db.execute(
                    "SELECT src FROM edges WHERE kind='PASS_USES_PATTERN' AND dst=? "
                    "LIMIT 1", (e[1],)).fetchone()
                ev = s.db.execute(
                    "SELECT file,line_start,confidence FROM evidence WHERE edge_id=? "
                    "LIMIT 1", (e[0],)).fetchone()
                out.append({"consumer": repo, "producer": prod_repo,
                            "artifact": f"op:{oname}",
                            "consumer_pass": pass_row[0] if pass_row else None,
                            "producer_dialect": own_dialect,
                            "confidence": (ev[2] if ev else "unknown"),
                            "evidence": {"file": ev[0], "line": ev[1]} if ev else None})
        return out

    def cross_repo_contracts(self, name=None):
        """Attribute names referenced in both repos -> contract records."""
        refs = {}
        for repo, s in self.repos:
            for a in s.nodes_by_kind(model.ATTRIBUTE):
                refs.setdefault(a["name"], {}).setdefault(repo, []).append(a)
        out = []
        for aname, per in sorted(refs.items()):
            if name and aname != name:
                continue
            if len(per) < 2:
                continue
            entry = {"attribute": aname, "repos": {}}
            for repo, s in self.repos:
                if repo not in per:
                    continue
                r = {}
                cr = s.db.execute(
                    "SELECT src FROM edges WHERE kind='CREATES_ATTRIBUTE' AND dst=?",
                    (f"attribute:{aname}",)).fetchall()
                rf = s.db.execute(
                    "SELECT COUNT(*) FROM edges WHERE kind='REFERENCES' AND dst=?",
                    (f"attribute:{aname}",)).fetchone()[0]
                r["creators"] = [c[0] for c in cr]
                r["reference_count"] = rf
                entry["repos"][repo] = r
            out.append(entry)
        return out

    def repository_boundary(self, repo_name):
        """Everything repo_name consumes from / hands to other repos."""
        return {"repo": repo_name,
                "consumes_dialects": [h for h in self.dialect_handoffs()
                                      if h["consumer"] == repo_name],
                "produces_dialects_to": [h for h in self.dialect_handoffs()
                                         if h["producer"] == repo_name],
                "op_handoffs_out": [h for h in self.op_handoffs()
                                    if h["consumer"] == repo_name],
                "attribute_contracts": [c for c in self.cross_repo_contracts()
                                        if repo_name in c["repos"]]}

    def status(self):
        return {"repos": {r: s.counts() for r, s in self.repos}}
