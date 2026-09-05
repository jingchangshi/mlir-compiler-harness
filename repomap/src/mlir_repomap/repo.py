"""Git facts: root, HEAD, branch, tracked files, dirty status, change detection."""

import os
import subprocess


def _git(root, *args):
    try:
        out = subprocess.run(["git", "-C", root, *args], capture_output=True,
                             text=True, timeout=60)
        if out.returncode != 0:
            return None
        return out.stdout
    except (OSError, subprocess.TimeoutExpired):
        return None


def find_repo_root(path):
    out = _git(path, "rev-parse", "--show-toplevel")
    if out:
        return out.strip()
    return os.path.abspath(path)


def git_facts(root):
    head = _git(root, "rev-parse", "HEAD")
    branch = _git(root, "rev-parse", "--abbrev-ref", "HEAD")
    return {"head": head.strip() if head else None,
            "branch": branch.strip() if branch else None,
            "is_git": head is not None}


def tracked_files(root, extra_excludes=None):
    """Return dict {relpath: content_hash} for tracked (or walked) files."""
    files = {}
    out = _git(root, "ls-files", "-z")
    if out is not None:
        for p in out.split("\0"):
            if p:
                files[p] = None
    else:
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in (".git", "build", "third-party", "third_party")]
            for f in filenames:
                rel = os.path.relpath(os.path.join(dirpath, f), root)
                files[rel] = None
    _fill_hashes(root, files, extra_excludes or [])
    return files


def _fill_hashes(root, files, excludes):
    excludes = [e.rstrip("/") for e in excludes]
    to_hash = [p for p in files
               if not any(p == e or p.startswith(e + "/") for e in excludes)]
    # batch via git hash-object when possible (fast, respects nothing else)
    out = _git(root, "hash-object", "--stdin-paths")  # needs stdin paths
    paths = "\n".join(to_hash)
    try:
        proc = subprocess.run(["git", "-C", root, "hash-object", "--stdin-paths"],
                              input=paths, capture_output=True, text=True, timeout=300)
        if proc.returncode == 0:
            hashes = proc.stdout.split()
            if len(hashes) == len(to_hash):
                for p, h in zip(to_hash, hashes):
                    files[p] = h
                return
    except (OSError, subprocess.TimeoutExpired):
        pass
    # fallback: manual hashing (dirty tree / not a git repo)
    import hashlib
    for p in to_hash:
        try:
            with open(os.path.join(root, p), "rb") as fh:
                files[p] = hashlib.sha1(fh.read()).hexdigest()
        except OSError:
            files[p] = "MISSING"


def changed_vs_head(root):
    """Files added/modified/deleted/renamed in working tree vs HEAD."""
    out = _git(root, "status", "--porcelain", "-z")
    result = {"added": [], "modified": [], "deleted": [], "renamed": []}
    if out is None:
        return None
    tokens = out.split("\0")
    i = 0
    while i < len(tokens):
        t = tokens[i]
        if not t:
            i += 1
            continue
        code, _, name = t.partition(" ")
        name = name.strip()
        if code.startswith("R"):
            old, new = name, tokens[i + 1] if i + 1 < len(tokens) else ""
            result["renamed"].append({"from": old, "to": new})
            i += 2
            continue
        i += 1
        if code in ("A", "??"):
            result["added"].append(name)
        elif code in ("M", "T", "AM", "MM"):
            result["modified"].append(name)
        elif code == "D":
            result["deleted"].append(name)
    return result


def diff_vs_base(root, base):
    out = _git(root, "diff", "--name-only", "-z", base)
    if out is None:
        return None
    return [p for p in out.split("\0") if p]
