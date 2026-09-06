"""Compiler findings: doc-layer lifecycle artifacts with git-aware drift tracking.

A finding is an agent-written YAML document (one file ``<ID>.yaml`` per finding)
recording a compiler-engineering observation: an unguarded invariant, a coverage
gap, a performance opportunity, a historical regression concern.  Findings are
deliberately NOT graph entities (ADR-020): the graph stays a facts-only contract.
This module provides only deterministic services over the finding documents:

* a strict YAML-subset parser with fail-soft diagnostics (stdlib only),
* schema + lifecycle validation (every status transition needs reason and
  evidence or a reference),
* git drift detection: commits touching evidence files since the finding's
  baseline commit, plus snippet-presence verification of recorded evidence.

The service never mutates a finding's status automatically — ``check()`` only
reports "needs review"; updating the document is a human/agent decision.
"""

import os
import re
import subprocess

CATEGORIES = ("correctness", "coverage", "performance", "architecture",
              "opportunity")
STATUSES = ("open", "acknowledged", "in-progress", "resolved", "rejected",
            "superseded")
RISKS = ("low", "medium", "high")
ENTITY_REF_KINDS = ("pass", "pattern", "attribute", "op", "operation",
                    "pipeline", "function", "dialect")

_REQUIRED = ("id", "category", "pass", "statement", "evidence", "reasoning",
             "status", "created_at")


class YamlSubsetError(ValueError):
    pass


# ---------------------------------------------------------------- YAML subset

def _scalar(text, source, lineno):
    s = text.strip()
    if len(s) >= 2 and s[0] == s[-1] and s[0] in "\"'":
        body = s[1:-1]
        return body.replace('\\"', '"') if s[0] == '"' else body.replace("''", "'")
    if s in ("true", "True"):
        return True
    if s in ("false", "False"):
        return False
    if s in ("~", "null", ""):
        return None
    if re.fullmatch(r"-?\d+", s):
        return int(s)
    if s[0] in "[{":
        raise YamlSubsetError(
            f"{source}:{lineno}: flow style ({s[:20]}...) not supported by the "
            "finding YAML subset; use block lists/mappings")
    return s


class _Parser:
    """Indentation-based parser for the finding-document YAML subset.

    Supported: mappings, lists (scalars or mappings), block scalars
    (``|``, ``|-``, ``>``, ``>-``), quoted/unquoted scalars, full-line comments.
    No flow style, no anchors, no tabs, no inline comments (quote values that
    contain ``#``).
    """

    def __init__(self, text, source):
        self.source = source
        self.lines = text.replace("\ufeff", "").splitlines()
        self.i = 0

    def parse(self):
        val = self._map(0)
        p = self._peek()
        if p is not None:
            raise YamlSubsetError(
                f"{self.source}:{p[2]}: unexpected content outside any mapping")
        return val

    def _peek(self):
        while self.i < len(self.lines):
            raw = self.lines[self.i]
            stripped = raw.strip()
            if not stripped or stripped.startswith("#"):
                self.i += 1
                continue
            indent = len(raw) - len(raw.lstrip(" "))
            ws = raw[:len(raw) - len(raw.lstrip())]
            if "\t" in ws:
                raise YamlSubsetError(
                    f"{self.source}:{self.i + 1}: tabs are not allowed for indentation")
            return indent, stripped, self.i + 1
        return None

    def _map(self, min_indent):
        out = {}
        while True:
            p = self._peek()
            if p is None or p[0] < min_indent:
                return out
            indent, content, lineno = p
            if p[0] > min_indent and out:
                raise YamlSubsetError(
                    f"{self.source}:{lineno}: unexpected indent (expected {min_indent})")
            m = re.match(r'("[^"]*"|\'[^\']*\'|[^:]+):(.*)$', content)
            if not m:
                raise YamlSubsetError(
                    f"{self.source}:{lineno}: expected 'key: value', got: {content[:40]}")
            key = _scalar(m.group(1), self.source, lineno)
            rest = m.group(2).strip()
            self.i += 1
            if rest in ("|", "|-", "|+", ">", ">-", ">+"):
                out[key] = self._block_scalar(indent, rest)
            elif rest == "":
                nxt = self._peek()
                if nxt and nxt[0] > indent:
                    out[key] = self._list(nxt[0]) if nxt[1].startswith("- ") \
                        else self._map(nxt[0])
                elif nxt and nxt[0] == indent and nxt[1].startswith("- "):
                    out[key] = self._list(indent)
                else:
                    out[key] = None
            else:
                out[key] = _scalar(rest, self.source, lineno)

    def _list(self, item_indent):
        items = []
        while True:
            p = self._peek()
            if p is None or p[0] != item_indent or not p[1].startswith("- "):
                return items
            indent, content, lineno = p
            rest = content[2:].strip()
            if rest == "":
                self.i += 1
                nxt = self._peek()
                if nxt and nxt[0] > indent:
                    items.append(self._map(nxt[0]))
                else:
                    items.append(None)
            elif ":" in rest and rest[0] not in "\"'":
                # rewrite "- key: value" as an ordinary mapping line and parse
                # the item's remaining keys at the dash-content indent
                self.lines[self.i] = " " * (indent + 2) + rest
                items.append(self._map(indent + 2))
            else:
                items.append(_scalar(rest, self.source, lineno))
                self.i += 1

    def _block_scalar(self, key_indent, style):
        folded = style.startswith(">")
        raw, base = [], None
        while self.i < len(self.lines):
            line = self.lines[self.i]
            if not line.strip():
                raw.append("")
                self.i += 1
                continue
            indent = len(line) - len(line.lstrip(" "))
            if indent <= key_indent:
                break
            if base is None:
                base = indent
            raw.append(line[base:] if indent >= base else line[indent:])
            self.i += 1
        while raw and raw[-1] == "":
            raw.pop()
        if folded:
            parts, buf = [], []
            for ln in raw:
                if ln == "":
                    if buf:
                        parts.append(" ".join(buf))
                        buf = []
                    parts.append("")
                else:
                    buf.append(ln.strip())
            if buf:
                parts.append(" ".join(buf))
            text = "\n".join(parts)
        else:
            text = "\n".join(raw)
        return text.rstrip("\n")


def parse_finding_text(text, source="<text>"):
    return _Parser(text, source).parse()


# ----------------------------------------------------------------- validation

def _err(errors, source, msg):
    errors.append(f"{source}: {msg}")


def validate_finding(data, source="<finding>"):
    """Return a list of error strings; empty means valid."""
    errors = []
    if not isinstance(data, dict) or set(data) != {"finding"}:
        _err(errors, source, "document must be a single top-level 'finding' mapping")
        return errors
    f = data["finding"]
    if not isinstance(f, dict):
        _err(errors, source, "'finding' must be a mapping")
        return errors
    for key in _REQUIRED:
        if f.get(key) in (None, "", []):
            _err(errors, source, f"missing required field: {key}")
    if f.get("category") not in CATEGORIES:
        _err(errors, source, f"category must be one of {CATEGORIES}")
    if f.get("status") not in STATUSES:
        _err(errors, source, f"status must be one of {STATUSES}")
    ev = f.get("evidence")
    if not isinstance(ev, list) or not ev:
        _err(errors, source, "evidence must be a non-empty list")
    else:
        for n, item in enumerate(ev):
            if not isinstance(item, dict) or not isinstance(item.get("file"), str) \
                    or not item.get("file"):
                _err(errors, source, f"evidence[{n}] must be a mapping with 'file'")
            elif item.get("lines") is not None and \
                    not _valid_lines(item["lines"]):
                _err(errors, source,
                     f"evidence[{n}].lines must be N or N-M, got {item['lines']!r}")
    history = f.get("history") or []
    seen = set()
    for n, h in enumerate(history):
        if not isinstance(h, dict):
            _err(errors, source, f"history[{n}] must be a mapping")
            continue
        if h.get("status") not in STATUSES:
            _err(errors, source, f"history[{n}].status must be one of {STATUSES}")
        seen.add(h.get("status"))
        if not h.get("reason"):
            _err(errors, source, f"history[{n}] requires a reason (ADR-020)")
        if not h.get("evidence") and not h.get("reference"):
            _err(errors, source,
                 f"history[{n}] requires evidence or a reference (ADR-020)")
        if h.get("status") == "superseded" and not h.get("superseded_by") \
                and not f.get("superseded_by"):
            _err(errors, source, "superseded requires 'superseded_by'")
    if f.get("status") in ("resolved", "rejected", "superseded") \
            and f.get("status") not in seen and not history:
        _err(errors, source,
             f"status {f['status']} requires a matching history entry")
    if f.get("status") == "superseded" and not f.get("superseded_by"):
        _err(errors, source, "superseded finding requires 'superseded_by'")
    reg = f.get("regression")
    if reg is not None:
        if not isinstance(reg, dict):
            _err(errors, source, "regression must be a mapping")
        elif reg.get("regression_risk") is not None \
                and reg.get("regression_risk") not in RISKS:
            _err(errors, source, f"regression_risk must be one of {RISKS}")
    # entity_refs (Phase 16): references to EXISTING graph entities only —
    # a finding never creates facts; kind keys are validated, ids at query time
    er = f.get("entity_refs")
    if er is not None:
        if not isinstance(er, list):
            _err(errors, source, "entity_refs must be a list")
        else:
            for n, item in enumerate(er):
                if not isinstance(item, dict) or len(item) != 1 \
                        or list(item)[0] not in ENTITY_REF_KINDS \
                        or not str(list(item.values())[0] or "").strip():
                    _err(errors, source,
                         f"entity_refs[{n}] must be 'kind: entity-id' with "
                         f"kind in {ENTITY_REF_KINDS}")
    return errors


def _valid_lines(lines):
    if isinstance(lines, int):
        return lines > 0
    return bool(isinstance(lines, str) and re.fullmatch(r"\d+(-\d+)?", lines))


# ------------------------------------------------------------------- git tools

def _git(repo, *args):
    try:
        out = subprocess.run(["git", "-C", repo, *args], capture_output=True,
                             text=True, timeout=60)
        if out.returncode != 0:
            return None
        return out.stdout
    except (OSError, subprocess.TimeoutExpired):
        return None


def _norm(s):
    return " ".join(s.split())


def _line_start(lines):
    if isinstance(lines, int):
        return lines
    if isinstance(lines, str):
        return int(lines.split("-")[0])
    return None


# -------------------------------------------------------------------- service

class FindingService:
    """Deterministic services over a directory of finding documents."""

    def __init__(self, findings_dir, repo=None):
        self.findings_dir = findings_dir
        self.repo = repo

    def load(self):
        findings, diagnostics = [], []
        if not os.path.isdir(self.findings_dir):
            diagnostics.append(f"findings directory not found: {self.findings_dir}")
            return findings, diagnostics
        for name in sorted(os.listdir(self.findings_dir)):
            if not name.endswith((".yaml", ".yml")):
                continue
            path = os.path.join(self.findings_dir, name)
            try:
                with open(path, encoding="utf-8") as fh:
                    data = parse_finding_text(fh.read(), path)
            except (OSError, YamlSubsetError) as exc:
                diagnostics.append(str(exc))
                continue
            errors = validate_finding(data, path)
            if errors:
                diagnostics.extend(errors)
                continue
            findings.append({"file": name, "data": data["finding"]})
        return findings, diagnostics

    def list(self, status=None, pass_name=None, category=None,
             has_regression=None):
        findings, diagnostics = self.load()
        rows = []
        for f in findings:
            d = f["data"]
            if status and d.get("status") != status:
                continue
            if pass_name and pass_name.lower() not in str(d.get("pass", "")).lower():
                continue
            if category and d.get("category") != category:
                continue
            if has_regression is not None and \
                    bool(d.get("regression")) != has_regression:
                continue
            statement = _norm(str(d.get("statement", "")))
            rows.append({
                "id": d.get("id"), "category": d.get("category"),
                "pass": d.get("pass"), "status": d.get("status"),
                "created_at": d.get("created_at"),
                "regression": bool(d.get("regression")),
                "statement": statement[:160] + ("..." if len(statement) > 160 else ""),
                "evidence_files": sorted({e.get("file") for e in d.get("evidence", [])
                                           if e.get("file")}),
            })
        return {"findings": rows, "count": len(rows), "diagnostics": diagnostics}

    def show(self, fid):
        findings, diagnostics = self.load()
        for f in findings:
            if str(f["data"].get("id", "")).lower() == str(fid).lower():
                return {"finding": f["data"], "file": f["file"],
                        "diagnostics": diagnostics}
        return {"error": "not found", "id": fid, "diagnostics": diagnostics}

    # -- git-aware drift checking -------------------------------------------

    def check(self, since=None, max_commits=20):
        findings, diagnostics = self.load()
        results = []
        head = _git(self.repo, "rev-parse", "HEAD").strip() if self.repo else None
        for f in findings:
            d = f["data"]
            entry = {"id": d.get("id"), "pass": d.get("pass"),
                     "status": d.get("status"), "file": f["file"]}
            baseline = since or (d.get("review") or {}).get("baseline_commit")
            if not head:
                entry.update(checked=False, needs_review=None,
                             reason=f"not a git repository: {self.repo}")
            elif not baseline:
                entry.update(
                    checked=False, needs_review=None,
                    reason="no baseline: record review.baseline_commit in the "
                           "finding or pass --since")
            elif _git(self.repo, "rev-parse", "--verify",
                      f"{baseline}^{{commit}}") is None:
                entry.update(checked=False, needs_review=None,
                             reason=f"baseline commit not found: {baseline}")
            else:
                entry.update(**self._check_one(d, baseline, head, max_commits))
            results.append(entry)
        summary = {
            "findings": len(results),
            "needs_review": sum(1 for r in results if r.get("needs_review")),
            "clean": sum(1 for r in results if r.get("checked") and
                         not r.get("needs_review")),
            "unchecked": sum(1 for r in results if not r.get("checked")),
            "diagnostics": diagnostics,
        }
        return {"summary": summary, "results": results,
                "baseline": since, "head": head}

    def _check_one(self, d, baseline, head, max_commits):
        commits, notes = [], []
        evidence_changed = False
        snippets_verified = 0
        by_file = {}
        for ev in d.get("evidence", []):
            if not ev.get("file"):
                continue
            if ev.get("repo"):
                notes.append(f"external-repo evidence ({ev['repo']}) not "
                             f"drift-checked here: {ev['file']}")
                continue
            by_file.setdefault(ev["file"], []).append(ev)
        for path in sorted(by_file):
            log = _git(self.repo, "log", "--format=%H%x1f%h%x1f%ad%x1f%s",
                       "--date=short", f"{baseline}..{head}", "--", path)
            if log is None:
                notes.append(f"git log failed for {path}")
            for line in filter(None, (log or "").splitlines()):
                full, short, date, subject = line.split("\x1f", 3)
                if not any(c["sha"] == short for c in commits):
                    commits.append({"sha": short, "date": date,
                                    "subject": subject})
            if not os.path.exists(os.path.join(self.repo, path)) and \
                    _git(self.repo, "cat-file", "-e", f"{head}:{path}") is None:
                evidence_changed = True
                notes.append(f"evidence file no longer present: {path}")
            for ev in by_file[path]:
                snippet = ev.get("snippet")
                if not snippet:
                    continue
                where = self._snippet_status(path, snippet, ev.get("lines"))
                if where == "missing":
                    evidence_changed = True
                    notes.append(f"evidence snippet no longer present in "
                                 f"{path}: {_norm(snippet)[:60]!r}")
                elif where == "moved":
                    notes.append(f"snippet moved within {path} "
                                 f"(recorded lines {ev.get('lines')})")
                else:
                    snippets_verified += 1
        truncated = len(commits) > max_commits
        commits = commits[:max_commits]
        needs_review = bool(commits) or evidence_changed
        if evidence_changed:
            verdict = "evidence changed — needs review"
        elif commits:
            first = commits[0]
            more = f" (+{len(commits) - 1} more)" if len(commits) > 1 else ""
            verdict = (f"possibly affected by commit {first['sha']} "
                       f"({first['subject']}){more}")
        else:
            verdict = f"no drift since baseline {baseline[:12]}"
        return {"checked": True, "needs_review": needs_review,
                "affected_by": commits, "truncated": truncated,
                "evidence_changed": evidence_changed,
                "snippets_verified": snippets_verified, "notes": notes,
                "verdict": verdict}

    def _snippet_status(self, path, snippet, lines):
        abs_path = os.path.join(self.repo, path)
        if not os.path.exists(abs_path):
            return "missing"
        with open(abs_path, encoding="utf-8", errors="replace") as fh:
            text = fh.read()
        if snippet in text:
            start = _line_start(lines)
            if start:
                window = text.splitlines(True)[max(0, start - 1 - 15):
                                               start - 1 + 15]
                if snippet in "".join(window):
                    return "same"
            return "moved"
        if _norm(snippet) in _norm(text):
            return "moved"
        return "missing"
