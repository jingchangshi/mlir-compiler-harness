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
from .extractors import tablegen, cpppass, pipeline, pattern, tests, python
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
    if ext == ".py":
        return [python]
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
            p = json.loads(props)
            if p.get("tblgen_class"):
                class_to_pass[p["tblgen_class"]] = dst
                class_to_pass[p["tblgen_class"] + "Base"] = dst
        for src, dst, props in db.execute(
                "SELECT src, dst, props FROM edges WHERE kind='PASS_IMPLEMENTS'"):
            class_to_pass[dst.split(":", 1)[-1]] = src
        # candidates for ambiguous class names: every pass id the class can mean
        class_candidates = {}
        for dst, props in db.execute("SELECT dst, props FROM edges WHERE kind='DEFINES'"):
            p = json.loads(props)
            for key in ("tblgen_class", "cpp_class"):
                if p.get(key) and dst.startswith("pass:"):
                    class_candidates.setdefault(p[key], []).append(dst)
            if p.get("cpp_class") and p.get("impl_base") and dst.startswith("pass_class:"):
                cand = class_to_pass.get(p["impl_base"])
                if cand:
                    class_candidates.setdefault(p["cpp_class"], []).append(cand)
        # bridge: impl::<TdClass>Base<Concrete> -> concrete cpp class maps to the pass
        for dst, props in db.execute("SELECT dst, props FROM edges WHERE kind='DEFINES'"):
            p = json.loads(props)
            if p.get("impl_base") and p.get("cpp_class") and p["impl_base"] in class_to_pass:
                class_to_pass[p["cpp_class"]] = class_to_pass[p["impl_base"]]
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
            # upstream-MLIR idiom: td class carries a dialect prefix with no
            # `let constructor` (e.g. TritonGPUAccelerateMatmul / createAccelerateMatmulPass)
            cand_classes = [mid, mid + "Pass"]
            cand_classes += [c for c in class_to_pass
                             if c.endswith(mid) and c != mid + "Pass"]
            for cand in cand_classes:
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

        # cross-file dialect ownership: op/type/attr node id prefixes map to dialect ids
        # (per-file resolution fails because ops live in a different .td than the dialect)
        dialect_ids = set(r[0] for r in db.execute("SELECT id FROM nodes WHERE kind='dialect'"))
        for nid, kind, file in db.execute(
                "SELECT id, kind, file FROM nodes WHERE kind IN ('op','type','attr')"):
            stem = nid.split(":", 1)[-1]
            if stem.endswith("Op"):
                stem = stem[:-2]
            owner = None
            parts = stem.split("_")
            for i in range(len(parts) - 1, 0, -1):
                cand = "dialect:" + "_".join(parts[:i])
                if cand in dialect_ids:
                    owner = cand
                    break
            if owner is None:
                # type/attr defs often have no dialect prefix; match by directory name
                segs = (file or "").split("/")
                if "Dialect" in segs:
                    cand = "dialect:" + segs[segs.index("Dialect") + 1]
                    owner = cand if cand in dialect_ids else None
            if owner:
                cur = db.execute("SELECT 1 FROM edges WHERE src=? AND dst=? AND kind='DIALECT_OWNS'",
                                 (owner, nid)).fetchone()
                if not cur:
                    db.execute("INSERT INTO edges (src,dst,kind,props) VALUES (?,?,?,?)",
                               (owner, nid, "DIALECT_OWNS", '{"inferred": true}'))
                    if file:
                        db.execute(
                            "INSERT INTO evidence SELECT edge_id,?,?,?,?, 'resolve', ? "
                            "FROM edges WHERE src=? AND dst=? AND kind='DIALECT_OWNS'",
                            (file, 1, 1, "", "inferred", owner, nid))

        # rewrite pass_class:* sources to the owning pass (pattern + populator edges);
        # class names can collide across dialects (two FlattenOpsPass) -> locality pick
        def _pick_pass(cls, eid):
            cands = class_candidates.get(cls) or (
                [class_to_pass[cls]] if cls in class_to_pass else [])
            if len(cands) <= 1:
                return cands[0] if cands else None, None
            evrow = db.execute("SELECT file FROM evidence WHERE edge_id=? LIMIT 1",
                               (eid,)).fetchone()
            if evrow:
                parts = set(evrow[0].split("/"))
                for c in cands:
                    pn = (db.execute("SELECT file FROM nodes WHERE id=?",
                                     (c,)).fetchone() or [""])[0]
                    if pn and (set(pn.split("/")) & parts) - {
                            "bishengir", "lib", "include", "Transforms",
                            "Pipelines", "Dialect", "Passes.td"}:
                        return c, "same-dialect-heuristic"
            return cands[0], "ambiguous-class-name"

        # derive pass-level dialect transitions from pattern op ownership (Phase 10):
        # matched ops -> input dialect, created ops -> output dialect
        op_dialect = {}
        for dsrc, ddst in db.execute(
                "SELECT src, dst FROM edges WHERE kind='DIALECT_OWNS' AND src LIKE 'dialect:%'"):
            op_dialect[ddst] = dsrc
        pass_patterns = {}
        for src_, dst_ in db.execute(
                "SELECT src, dst FROM edges WHERE kind='PASS_USES_PATTERN'"):
            pass_patterns.setdefault(src_, set()).add(dst_)
        for src_, dst_ in db.execute(
                "SELECT src, dst FROM edges WHERE kind='PASS_USES_PATTERN_POPULATOR'"):
            stack, seen = [dst_], set()
            while stack:
                cur = stack.pop()
                if cur in seen:
                    continue
                seen.add(cur)
                for c in db.execute(
                        "SELECT dst FROM edges WHERE kind='FUNCTION_CALLS' AND src=?",
                        (cur,)):
                    stack.append(c[0])
                for pd in db.execute(
                        "SELECT dst FROM edges WHERE kind='FUNCTION_DEFINES_PATTERN' AND src=?",
                        (cur,)):
                    pass_patterns.setdefault(src_, set()).add(pd[0])
        for pas, pats in pass_patterns.items():
            ins, outs = set(), set()
            for pt in pats:
                for mo in db.execute(
                        "SELECT dst FROM edges WHERE kind='PATTERN_MATCHES_OP' AND src=?",
                        (pt,)):
                    d = op_dialect.get(mo[0])
                    if d:
                        ins.add(d)
                for co in db.execute(
                        "SELECT dst FROM edges WHERE kind='PATTERN_CREATES_OP' AND src=?",
                        (pt,)):
                    d = op_dialect.get(co[0])
                    if d:
                        outs.add(d)
            for role, ds, via in (("output", outs, "created-ops"),
                                  ("input", ins, "matched-ops")):
                for d in ds:
                    db.execute("INSERT OR IGNORE INTO edges (src,dst,kind,props) VALUES (?,?,?,?)",
                               (pas, d, "DIALECT_TRANSITIONS_TO",
                                '{"role": "%s", "via": "%s"}' % (role, via)))
                    db.execute("INSERT INTO evidence SELECT edge_id,?,?,0,?, 'resolve', ? "
                               "FROM edges WHERE src=? AND dst=? AND kind='DIALECT_TRANSITIONS_TO' "
                               "AND props LIKE '%via%%' AND props LIKE ? LIMIT 1",
                               (pas, d, "derived from pattern op ownership", "inferred",
                                pas, d, '%"' + via + '"%'))

        for kind in ("PASS_USES_PATTERN", "PASS_USES_PATTERN_POPULATOR",
                     "DIALECT_TRANSITIONS_TO", "CREATES_ATTRIBUTE",
                     "HAS_CONSTRAINT"):
            for eid, src in db.execute(
                    f"SELECT edge_id, src FROM edges WHERE kind='{kind}' "
                    "AND src LIKE 'pass_class:%'").fetchall():
                cls = src.split(":", 1)[-1]
                tgt, disamb = _pick_pass(cls, eid)
                if not tgt:
                    continue
                try:
                    db.execute("UPDATE edges SET src=? WHERE edge_id=?",
                               (tgt, eid))
                except sqlite3.IntegrityError:
                    # collision: an identical edge already exists for this pass;
                    # merge evidence and drop the duplicate
                    dup = db.execute(
                        "SELECT edge_id FROM edges WHERE src=? AND dst=(SELECT dst "
                        "FROM edges WHERE edge_id=?) AND kind=(SELECT kind FROM edges "
                        "WHERE edge_id=?) AND props=(SELECT props FROM edges WHERE "
                        "edge_id=?) AND edge_id<>?", (tgt, eid, eid, eid, eid)).fetchone()
                    if dup:
                        db.execute("UPDATE evidence SET edge_id=? WHERE edge_id=?",
                                   (dup[0], eid))
                        db.execute("DELETE FROM edges WHERE edge_id=?", (eid,))
                    continue
                if disamb:
                    # props change can collide with a persisted twin that already
                    # carries the disambiguation flag: merge instead of update
                    newp = db.execute(
                        "SELECT json_set(props,'$.disambiguation',?) FROM edges "
                        "WHERE edge_id=?", (disamb, eid)).fetchone()[0]
                    twin = db.execute(
                        "SELECT edge_id FROM edges WHERE src=? AND dst=? AND "
                        "kind=? AND props=? AND edge_id<>?",
                        (tgt, db.execute("SELECT dst FROM edges WHERE edge_id=?",
                                         (eid,)).fetchone()[0],
                         db.execute("SELECT kind FROM edges WHERE edge_id=?",
                                    (eid,)).fetchone()[0], newp, eid)).fetchone()
                    if twin:
                        db.execute("UPDATE evidence SET edge_id=? WHERE edge_id=?",
                                   (twin[0], eid))
                        db.execute("DELETE FROM edges WHERE edge_id=?", (eid,))
                    else:
                        db.execute("UPDATE edges SET props=json_set(props,"
                                   "'$.disambiguation',?) WHERE edge_id=?",
                                   (disamb, eid))
        # binding markers: BINDING_MAPS_TO -> function ids; PYTHON_COMPOSES -> bindings;
        # then expose passes through bindings (Python -> binding -> factory -> pass)
        binding_defs = {}
        for eid, dst, src_ in db.execute(
                "SELECT edge_id, dst, src FROM edges WHERE kind='BINDING_MAPS_TO'").fetchall():
            if dst.startswith("factory:"):
                binding_defs[src_] = dst  # lambda branch already resolved to the factory
                continue
            if not dst.startswith("function:NAME:"):
                continue
            nm = dst.split("function:NAME:", 1)[-1]
            # the mapped symbol is usually a C++ pass FACTORY (createXPass)
            fac = db.execute("SELECT id FROM nodes WHERE kind='factory' AND name=?",
                             (nm,)).fetchone()
            if fac:
                db.execute("UPDATE edges SET dst=? WHERE edge_id=?", (fac[0], eid))
                binding_defs[src_] = fac[0]
            else:
                ids = [r[0] for r in db.execute(
                    "SELECT id FROM nodes WHERE kind='function' AND name=?", (nm,))]
                if len(ids) == 1:
                    db.execute("UPDATE edges SET dst=? WHERE edge_id=?", (ids[0], eid))
                    binding_defs[src_] = ids[0]
                else:
                    db.execute("DELETE FROM evidence WHERE edge_id=?", (eid,))
                    db.execute("DELETE FROM edges WHERE edge_id=?", (eid,))
        # name-based binding markers from Python composers
        binding_ids = {}
        for bid in [r[0] for r in db.execute("SELECT id FROM nodes WHERE kind='binding'")]:
            binding_ids[bid.split(":", 1)[-1]] = bid
        for eid, dst in db.execute(
                "SELECT edge_id, dst FROM edges WHERE kind='PYTHON_COMPOSES' "
                "AND dst LIKE 'binding:NAME:%'").fetchall():
            nm = dst.split("binding:NAME:", 1)[-1]
            bid = binding_ids.get(nm)
            if bid:
                db.execute("UPDATE edges SET dst=? WHERE edge_id=?", (bid, eid))
            else:
                db.execute("DELETE FROM evidence WHERE edge_id=?", (eid,))
                db.execute("DELETE FROM edges WHERE edge_id=?", (eid,))
        # binding -> pass via the mapped C++ function being a known factory
        fac_to_pass_full = dict(fac_to_pass)
        for pas, fac in db.execute(
                "SELECT src, dst FROM edges WHERE kind='PASS_HAS_FACTORY'"):
            fac_to_pass_full[fac] = pas
        for bid, fnid in binding_defs.items():
            tgt = fac_to_pass_full.get(fnid)
            if not tgt:
                row = db.execute("SELECT dst FROM edges WHERE kind='PASS_HAS_FACTORY' "
                                 "AND dst=?", (fnid,)).fetchone()
                tgt = row[0] if row else None
            if tgt:
                db.execute("INSERT OR IGNORE INTO edges (src,dst,kind,props) "
                           "VALUES (?,?,?,?)",
                           (bid, tgt, "BINDING_EXPOSES_PASS", "{}"))

        # resolve cross-file populator call markers to function ids (QG-3)
        func_names = {}
        for fid, nm in db.execute("SELECT id, name FROM nodes WHERE kind='function'"):
            func_names.setdefault(nm, []).append(fid)
        for eid, dst in db.execute(
                "SELECT edge_id, dst FROM edges WHERE dst LIKE 'function:NAME:%' "
                "AND kind IN ('PASS_USES_PATTERN_POPULATOR','FUNCTION_CALLS')").fetchall():
            nm = dst.split("function:NAME:", 1)[-1]
            ids = func_names.get(nm, [])
            if len(ids) == 1:
                db.execute("UPDATE edges SET dst=? WHERE edge_id=?", (ids[0], eid))
            elif not ids:
                db.execute("DELETE FROM evidence WHERE edge_id=?", (eid,))
                db.execute("DELETE FROM edges WHERE edge_id=?", (eid,))
            else:
                db.execute("UPDATE edges SET props=json_set(props,'$.ambiguous_name',?) "
                           "WHERE edge_id=?", (nm, eid))

        # resolve name-based pipeline call markers to file-qualified pipeline ids (QG-1)
        pipe_names = {}
        for pid, nm in db.execute("SELECT id, name FROM nodes WHERE kind='pipeline'"):
            pipe_names.setdefault(nm, []).append(pid)
        for eid, dst in db.execute(
                "SELECT edge_id, dst FROM edges WHERE kind='PIPELINE_CALLS' "
                "AND dst LIKE 'pipeline:NAME:%'").fetchall():
            nm = dst.split("pipeline:NAME:", 1)[-1]
            ids = pipe_names.get(nm, [])
            if len(ids) == 1:
                db.execute("UPDATE edges SET dst=? WHERE edge_id=?", (ids[0], eid))
            elif len(ids) > 1:
                db.execute(
                    "UPDATE edges SET props=json_set(props,'$.ambiguous_name',?) "
                    "WHERE edge_id=?", (nm, eid))

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
