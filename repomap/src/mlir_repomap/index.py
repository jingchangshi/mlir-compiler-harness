"""Index orchestration: file selection, per-file extraction with caching, resolution.

Incremental model: per-file parse results are cached by content hash; only changed files
are re-parsed. Graph resolution (factory->pass, test->pass filtering) re-runs over the
whole graph after each build (cheap, deterministic).
"""
import json
import sqlite3
import os
import time

from . import model, repo
from .extractors import tablegen, cpppass, pipeline, pattern, tests
from .store import Store

DEFAULT_EXCLUDES = ["third-party", "third_party", "build", ".git", ".mlir-repomap",
                    "node_modules", "__pycache__"]

TEXT_EXTS = {".cpp", ".cc", ".h", ".hpp", ".td", ".inc", ".mlir", ".py", ".c"}


def _load_config(root):
    cfg = os.path.join(root, ".mlir-repomap.toml")
    conf = {"include": [], "exclude": list(DEFAULT_EXCLUDES)}
    if os.path.exists(cfg):
        try:
            import tomllib
            with open(cfg, "rb") as f:
                data = tomllib.load(f)
            conf.update({k: v for k, v in data.items() if k in ("include", "exclude")})
        except Exception:
            pass
    return conf


def _selected(rel, conf):
    if conf["include"] and not any(rel.startswith(p) for p in conf["include"]):
        return False
    parts = rel.split("/")
    if any(p in conf["exclude"] for p in parts):
        return False
    ext = os.path.splitext(rel)[1]
    return ext in TEXT_EXTS


def _extractors_for(rel):
    ext = os.path.splitext(rel)[1]
    if ext == ".td":
        return [tablegen]
    if ext in (".cpp", ".cc", ".h", ".hpp", ".c"):
        return [cpppass, pipeline, pattern]
    if ext == ".mlir":
        return [tests]
    return []


class Indexer:
    def __init__(self, root):
        self.root = root
        self.conf = _load_config(root)
        self.store = Store(root)

    def close(self):
        self.store.close()

    def build(self, full=False):
        t0 = time.time()
        facts = repo.git_facts(self.root)
        files = repo.tracked_files(self.root, extra_excludes=self.conf["exclude"])
        stored = {} if full else self.store.stored_files()
        # extractor logic changed => previous parse cache is invalid
        last = self.store.get_meta("last_build") or {}
        if not full and last.get("indexer_version") != model.INDEXER_VERSION:
            stored = {}
        stats = {"scanned": 0, "reextracted": 0, "unchanged": 0, "deleted": 0}
        parse_cache = {}

        for rel, h in files.items():
            if not _selected(rel, self.conf):
                continue
            stats["scanned"] += 1
            old = stored.get(rel)
            if old == h and old != "MISSING":
                stats["unchanged"] += 1
                continue
            self.store.drop_file(rel)
            if h == "MISSING" or old == "MISSING":
                stats["deleted"] += 1
                self.store.set_file_hash(rel, h)
                continue
            self.store.set_file_hash(rel, h)
            if h is None:
                continue
            try:
                with open(os.path.join(self.root, rel), "r", encoding="utf-8",
                          errors="replace") as fh:
                    text = fh.read()
            except OSError as e:
                self.store.record_diagnostic(rel, str(e))
                continue
            exs = _extractors_for(rel)
            if not exs:
                continue
            stats["reextracted"] += 1
            for ex in exs:
                try:
                    self.store.add_finding(ex.extract(rel, text))
                except Exception as e:  # fail soft
                    self.store.record_diagnostic(rel, f"{ex.__name__}: {e!r}")

        # remove hashes of files no longer present
        cur = set(self.store.stored_files())
        for gone in cur - set(files):
            self.store.drop_file(gone)

        self.resolve()
        stats["seconds"] = round(time.time() - t0, 1)
        self.store.set_meta("last_build", {"head": facts["head"], "branch": facts["branch"],
                                           "when": time.strftime("%Y-%m-%dT%H:%M:%S"),
                                           "stats": stats,
                                           "schema_version": model.SCHEMA_VERSION,
                                           "indexer_version": model.INDEXER_VERSION,
                                           "config": self.conf})
        return stats

    # ---- deterministic graph resolution (ADR-001) ----
    def resolve(self):
        db = self.store.db

        def _synth_pass(db, ref):
            """Create a cpp-only pass node for an unmapped factory reference."""
            fac = ref.split(":", 1)[-1]
            mid = fac[len("create"):-len("Pass")] if fac.startswith("create") else fac
            nid = f"pass:{mid}"
            db.execute("INSERT OR IGNORE INTO nodes VALUES (?,?,?,?,?,?)",
                       (nid, "pass", mid, "cpp-only pass (from factory reference)",
                        "", None))
            return nid

        # class -> pass id  (from td DEFINES props.tblgen_class and PASS_IMPLEMENTS edges)
        class_to_pass = {}
        for dst, props in db.execute("SELECT dst, props FROM edges WHERE kind='DEFINES'"):
            tc = json.loads(props).get("tblgen_class")
            if tc:
                class_to_pass[tc] = dst
        for src, dst in db.execute("SELECT src, dst FROM edges WHERE kind='PASS_IMPLEMENTS'"):
            class_to_pass[dst.split(":", 1)[-1]] = src
        # factory -> pass id(s); td `let constructor` links are authoritative (ADR-001).
        # A factory name may be ambiguous (same createXxxPass in several namespaces)
        # -> keep all candidates and disambiguate by locality at rewrite time.
        fac_candidates = {}
        for src, dst in db.execute("SELECT src, dst FROM edges WHERE kind='PASS_HAS_FACTORY'"):
            fac_candidates.setdefault(dst, []).append(src)
        fac_to_pass = {k: v[0] for k, v in fac_candidates.items()}
        for name in [r[0] for r in db.execute(
                "SELECT name FROM nodes WHERE kind='factory'")]:
            mid = name[len("create"):-len("Pass")] if name.startswith("create") else name
            for cand in (mid, mid + "Pass"):
                if cand in class_to_pass:
                    fac_to_pass[f"factory:{name}"] = class_to_pass[cand]
                    break

        # synthesize pass nodes for factory refs with no known pass entity
        # (cpp-only passes; confidence inferred, evidence remains on the edge)
        for kind in ("PIPELINE_CONTAINS", "PRECEDES"):
            for col in ("dst", "src"):
                for row in db.execute(
                        f"SELECT edge_id, {col} FROM edges WHERE kind='{kind}' "
                        f"AND {col} LIKE 'factory:%'").fetchall():
                    eid, ref = row
                    cands = fac_candidates.get(ref)
                    if cands:
                        if len(cands) == 1:
                            new, disamb = cands[0], None
                        else:
                            # same-dialect locality heuristic: match path component of
                            # the call-site evidence file against the pass def file
                            new, disamb = cands[0], "ambiguous"
                            evfile = db.execute("SELECT file FROM evidence WHERE edge_id=? "
                                                "LIMIT 1", (eid,)).fetchone()
                            if evfile:
                                parts = set(evfile[0].split("/"))
                                for c in cands:
                                    pn = (db.execute("SELECT file FROM nodes WHERE id=?",
                                                     (c,)).fetchone() or [""])[0]
                                    if pn and (set(pn.split("/")) & parts) - {"bishengir", "lib", "include", "Transforms", "Pipelines", "Dialect"}:
                                        new, disamb = c, "same-dialect-heuristic"
                                        break
                    else:
                        new, disamb = fac_to_pass.get(ref) or _synth_pass(db, ref), None
                    try:
                        db.execute(f"UPDATE edges SET {col}=? WHERE edge_id=?", (new, eid))
                        if disamb:
                            db.execute("UPDATE edges SET props=json_set(props,'$.disambiguation',?) "
                                       "WHERE edge_id=?", (disamb, eid))
                    except sqlite3.IntegrityError:
                        # merged into an existing identical edge: move evidence over
                        dup = db.execute(
                            "SELECT edge_id FROM edges WHERE src=(SELECT src FROM edges "
                            "WHERE edge_id=?) AND dst=? AND kind=(SELECT kind FROM edges "
                            "WHERE edge_id=?) AND props=(SELECT props FROM edges "
                            "WHERE edge_id=?) AND edge_id<>?",
                            (eid, new, eid, eid, eid)).fetchone()
                        if dup:
                            db.execute("UPDATE evidence SET edge_id=? WHERE edge_id=?",
                                       (dup[0], eid))
                            db.execute("DELETE FROM edges WHERE edge_id=?", (eid,))
                        # no dup found: keep the edge untouched rather than lose data
        # PASS_HAS_FACTORY edges
        for fac, pas in fac_to_pass.items():
            conf = model.CONFIRMED if pas.startswith("pass:") and not class_to_pass.get(
                fac[8:-4]) else model.CONFIRMED
            row = db.execute("SELECT 1 FROM edges WHERE src=? AND dst=? AND kind='PASS_HAS_FACTORY'",
                             (pas, fac)).fetchone()
            if not row:
                db.execute("INSERT INTO edges (src,dst,kind,props) VALUES (?,?,?,?)",
                           (pas, fac, "PASS_HAS_FACTORY", "{}"))

        # rewrite PASS_USES_PATTERN from pass_class:* to the owning pass when known
        for eid, src in db.execute(
                "SELECT edge_id, src FROM edges WHERE kind='PASS_USES_PATTERN' "
                "AND src LIKE 'pass_class:%'").fetchall():
            cls = src.split(":", 1)[-1]
            if cls in class_to_pass:
                db.execute("UPDATE edges SET src=? WHERE edge_id=?",
                           (class_to_pass[cls], eid))

        # test edges: keep only those hitting known passes; reroute pipeline flags
        pass_names = set(r[0] for r in db.execute("SELECT id FROM nodes WHERE kind='pass'"))
        pipe_names = set(r[0] for r in db.execute("SELECT name FROM nodes WHERE kind='pipeline'"))
        for eid, src, dst in db.execute(
                "SELECT edge_id, src, dst FROM edges WHERE kind='TEST_COVERS_PASS'").fetchall():
            flag = dst.split(":", 1)[-1]
            if dst in pass_names:
                continue
            hit = None
            for p in pipe_names:
                if flag.startswith(p) or flag.startswith(p + "-") or f"{p}-pipeline" == flag:
                    hit = p
                    break
            if hit:
                db.execute("UPDATE edges SET dst=?, kind=? WHERE edge_id=?",
                           (f"pipeline:{hit}", "TEST_EXERCISES_PIPELINE", eid))
            else:
                db.execute("DELETE FROM evidence WHERE edge_id=?", (eid,))
                db.execute("DELETE FROM edges WHERE edge_id=?", (eid,))
        db.commit()
