"""SQLite persistence: nodes, edges (+evidence), files, meta, diagnostics."""
import json
import os
import sqlite3
import time

from . import model

SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT);
CREATE TABLE IF NOT EXISTS nodes (
    id TEXT PRIMARY KEY, kind TEXT, name TEXT, summary TEXT,
    file TEXT, line INTEGER);
CREATE TABLE IF NOT EXISTS edges (
    edge_id INTEGER PRIMARY KEY AUTOINCREMENT,
    src TEXT, dst TEXT, kind TEXT, props TEXT);
CREATE UNIQUE INDEX IF NOT EXISTS edges_key ON edges (src, dst, kind, props);
CREATE TABLE IF NOT EXISTS evidence (
    edge_id INTEGER, file TEXT, line_start INTEGER, line_end INTEGER,
    snippet TEXT, extractor TEXT, confidence TEXT);
CREATE TABLE IF NOT EXISTS files (path TEXT PRIMARY KEY, hash TEXT);
CREATE TABLE IF NOT EXISTS diagnostics (file TEXT, message TEXT);
"""


class Store:
    def __init__(self, root, index_dir=".mlir-repomap"):
        self.dir = os.path.join(root, index_dir)
        os.makedirs(self.dir, exist_ok=True)
        self.path = os.path.join(self.dir, "index.db")
        self.db = sqlite3.connect(self.path)
        self.db.executescript(SCHEMA)

    def close(self):
        self.db.commit()
        self.db.close()

    # ---- meta ----
    def set_meta(self, key, value):
        self.db.execute("INSERT OR REPLACE INTO meta VALUES (?,?)", (key, json.dumps(value)))

    def get_meta(self, key, default=None):
        row = self.db.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
        return json.loads(row[0]) if row else default

    # ---- files ----
    def stored_files(self):
        return dict(self.db.execute("SELECT path, hash FROM files"))

    def set_file_hash(self, path, h):
        self.db.execute("INSERT OR REPLACE INTO files VALUES (?,?)", (path, h))

    def drop_file(self, path):
        """Remove all graph content sourced from a file (invalidation)."""
        self.db.execute("DELETE FROM nodes WHERE file=?", (path,))
        self.db.execute("DELETE FROM evidence WHERE file=?", (path,))
        self.db.execute("DELETE FROM edges WHERE edge_id NOT IN "
                        "(SELECT DISTINCT edge_id FROM evidence)")
        self.db.execute("DELETE FROM files WHERE path=?", (path,))
        self.db.execute("DELETE FROM diagnostics WHERE file=?", (path,))

    def clear_diagnostics(self, path):
        self.db.execute("DELETE FROM diagnostics WHERE file=?", (path,))

    def record_diagnostic(self, path, message):
        self.db.execute("INSERT OR REPLACE INTO diagnostics VALUES (?,?)", (path, message))

    # ---- graph ----
    def add_finding(self, f):
        for n in f["nodes"]:
            self.db.execute("INSERT OR REPLACE INTO nodes VALUES (?,?,?,?,?,?)",
                            (n["id"], n["kind"], n["name"], n["summary"], n["file"], n["line"]))
        for e in f["edges"]:
            props = json.dumps(e.get("props") or {}, sort_keys=True)
            cur = self.db.execute(
                "SELECT edge_id FROM edges WHERE src=? AND dst=? AND kind=? AND props=?",
                (e["src"], e["dst"], e["kind"], props))
            row = cur.fetchone()
            if row:
                edge_id = row[0]
            else:
                edge_id = self.db.execute(
                    "INSERT INTO edges (src,dst,kind,props) VALUES (?,?,?,?)",
                    (e["src"], e["dst"], e["kind"], props)).lastrowid
            ev = e.get("evidence")
            if ev:
                self.db.execute(
                    "INSERT INTO evidence VALUES (?,?,?,?,?,?,?)",
                    (edge_id, ev["file"], ev["line_start"], ev.get("line_end") or ev["line_start"],
                     ev.get("snippet", ""), ev.get("extractor", ""), ev.get("confidence", "")))

    def node(self, nid):
        row = self.db.execute("SELECT id,kind,name,summary,file,line FROM nodes WHERE id=?",
                              (nid,)).fetchone()
        if not row:
            return None
        return {"id": row[0], "kind": row[1], "name": row[2], "summary": row[3],
                "file": row[4], "line": row[5]}

    def nodes_by_kind(self, kind):
        return [dict(zip(("id", "kind", "name", "summary", "file", "line"), r))
                for r in self.db.execute(
                    "SELECT id,kind,name,summary,file,line FROM nodes WHERE kind=? "
                    "ORDER BY name", (kind,))]

    def edges_from(self, nid, kind=None):
        if kind:
            rows = self.db.execute(
                "SELECT edge_id,src,dst,kind,props FROM edges WHERE src=? AND kind=?", (nid, kind))
        else:
            rows = self.db.execute("SELECT edge_id,src,dst,kind,props FROM edges WHERE src=?", (nid,))
        return [self._edge(r) for r in rows]

    def edges_to(self, nid, kind=None):
        if kind:
            rows = self.db.execute(
                "SELECT edge_id,src,dst,kind,props FROM edges WHERE dst=? AND kind=?", (nid, kind))
        else:
            rows = self.db.execute("SELECT edge_id,src,dst,kind,props FROM edges WHERE dst=?", (nid,))
        return [self._edge(r) for r in rows]

    def _edge(self, r):
        e = {"edge_id": r[0], "src": r[1], "dst": r[2], "kind": r[3],
             "props": json.loads(r[4])}
        evrows = self.db.execute(
            "SELECT file,line_start,line_end,snippet,extractor,confidence FROM evidence "
            "WHERE edge_id=?", (r[0],)).fetchall()
        e["evidence"] = [{"file": x[0], "line_start": x[1], "line_end": x[2],
                          "snippet": x[3], "extractor": x[4], "confidence": x[5]}
                         for x in evrows]
        return e

    def counts(self):
        return dict(self.db.execute("SELECT kind, COUNT(*) FROM nodes GROUP BY kind"))

    def search_nodes(self, needle):
        like = f"%{needle}%"
        return [dict(zip(("id", "kind", "name", "summary", "file", "line"), r))
                for r in self.db.execute(
                    "SELECT id,kind,name,summary,file,line FROM nodes "
                    "WHERE name LIKE ? OR id LIKE ? ORDER BY kind,name LIMIT 100",
                    (like, like))]
