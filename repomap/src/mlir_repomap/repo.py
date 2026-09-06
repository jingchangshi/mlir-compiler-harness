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
        # Porcelain v1 has a fixed two-character XY status followed by a
        # space and the path.  ``partition(' ')`` loses a leading blank in
        # ordinary unstaged states (`` M path``), so it silently missed them.
        code, name = t[:2], t[3:]
        if "R" in code:
            # With ``-z``, porcelain v1 emits destination first, then source.
            new, old = name, tokens[i + 1] if i + 1 < len(tokens) else ""
            result["renamed"].append({"from": old, "to": new})
            i += 2
            continue
        i += 1
        if code == "??" or "A" in code:
            result["added"].append(name)
        elif "M" in code or "T" in code:
            result["modified"].append(name)
        elif "D" in code:
            result["deleted"].append(name)
    return result


def worktree_snapshot(root):
    """Return a stable representation of the working tree state.

    An index may intentionally be built from a dirty tree.  Keeping the
    snapshot taken at build time lets callers distinguish that case from a
    source change made *after* the index was built.  This is deliberately
    based on git-status paths rather than timestamps or generated index contents.
    """
    dirty = changed_vs_head(root)
    if dirty is None:
        return None
    return {
        "added": sorted(dirty.get("added") or []),
        "modified": sorted(dirty.get("modified") or []),
        "deleted": sorted(dirty.get("deleted") or []),
        "renamed": sorted(dirty.get("renamed") or [],
                          key=lambda item: (item.get("from", ""),
                                            item.get("to", ""))),
    }


def diff_vs_base(root, base):
    out = _git(root, "diff", "--name-only", "-z", base)
    if out is None:
        return None
    return [p for p in out.split("\0") if p]
