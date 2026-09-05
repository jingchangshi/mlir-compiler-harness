"""Thin CLI frontend over QueryService (ADR-004: no business logic here)."""
import argparse
import json
import os
import sys


def _findings_text(result):
    lines = []
    for r in result["results"]:
        lines.append(f"Finding {r.get('id')}")
        if not r.get("checked"):
            lines.append(f"not checked: {r.get('reason')}")
        elif r.get("needs_review"):
            lines.append(r["verdict"])
            lines.append("Needs review")
        else:
            lines.append(r["verdict"])
    s = result["summary"]
    lines.append(f"{s['findings']} findings: {s['needs_review']} need review, "
                 f"{s['clean']} clean, {s['unchecked']} unchecked")
    return "\n".join(lines)


def main(argv=None):
    from . import index as index_mod
    from .query import QueryService

    ap = argparse.ArgumentParser(prog="mlir-repomap",
                                 description="MLIR compiler repository analysis harness")
    ap.add_argument("--repo", default=".", help="repository root (default: cwd)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    ap.add_argument("--reindex", action="store_true", help="force full re-index")
    sub.add_parser("status")
    p = sub.add_parser("modules"); p.add_argument("--depth", type=int, default=2)
    sub.add_parser("dialects")
    p = sub.add_parser("passes"); p.add_argument("query", nargs="?")
    p = sub.add_parser("pass"); p.add_argument("name")
    sub.add_parser("pipelines")
    p = sub.add_parser("pipeline"); p.add_argument("name"); p.add_argument("--brief", action="store_true")
    p = sub.add_parser("symbol"); p.add_argument("name")
    p = sub.add_parser("references"); p.add_argument("name")
    p = sub.add_parser("tests"); p.add_argument("name")
    p = sub.add_parser("changed"); p.add_argument("base", nargs="?")
    p = sub.add_parser("evidence"); p.add_argument("ident")
    p = sub.add_parser("pattern-owner"); p.add_argument("name")
    p = sub.add_parser("pipeline-builder"); p.add_argument("name")
    p = sub.add_parser("attribute"); p.add_argument("name")
    p = sub.add_parser("attribute-provenance"); p.add_argument("name")
    p = sub.add_parser("pipeline-composition"); p.add_argument("name")
    eco = sub.add_parser("ecosystem")
    eco.add_argument("--repos", action="append", required=True)
    eco.add_argument("query", choices=["status", "handoff", "boundary", "contract"])
    eco.add_argument("name", nargs="?")
    p = sub.add_parser("dialect-transition"); p.add_argument("name")
    p = sub.add_parser("semantic-contract"); p.add_argument("name")
    p = sub.add_parser("boundary"); p.add_argument("name")
    p = sub.add_parser("pass-intent"); p.add_argument("name")
    p = sub.add_parser("pass-constraints"); p.add_argument("name")
    p = sub.add_parser("index"); p.add_argument("--full", action="store_true")
    fin = sub.add_parser("findings")
    fsub = fin.add_subparsers(dest="fsub", required=True)
    fl = fsub.add_parser("list")
    fl.add_argument("--status"); fl.add_argument("--pass-name")
    fl.add_argument("--category"); fl.add_argument("--dir")
    fl.add_argument("--has-regression", action="store_true")
    fc = fsub.add_parser("check")
    fc.add_argument("--since"); fc.add_argument("--dir"); fc.add_argument("--git-repo")
    fc.add_argument("--format", choices=["json", "text"], default="json")
    fs = fsub.add_parser("show"); fs.add_argument("fid"); fs.add_argument("--dir")

    args = ap.parse_args(argv)
    root = args.repo

    if args.cmd == "findings":
        from .findings import FindingService
        fdir = args.dir or os.path.join(root, "docs", "compiler-architecture",
                                        "findings")
        git_repo = getattr(args, "git_repo", None) or root
        svc = FindingService(fdir, repo=git_repo)
        if args.fsub == "list":
            result = svc.list(status=args.status, pass_name=args.pass_name,
                              category=args.category,
                              has_regression=bool(args.has_regression) or None)
        elif args.fsub == "check":
            result = svc.check(since=args.since)
            if args.format == "text":
                print(_findings_text(result))
                return 0
        else:
            result = svc.show(args.fid)
        print(json.dumps({"command": "findings", "result": result},
                         indent=1, default=str))
        return 0

    if args.cmd == "ecosystem":
        from .ecosystem import EcosystemQueryService
        eco = EcosystemQueryService(args.repos)
        try:
            q = args.query
            if q == "status":
                result = eco.status()
            elif q == "handoff":
                result = {"handoffs": eco.dialect_handoffs(args.name)
                          + eco.op_handoffs(args.name)}
            elif q == "boundary":
                result = eco.repository_boundary(
                    args.name or os.path.basename(os.path.abspath(args.repos[0])))
            else:
                result = {"contracts": eco.cross_repo_contracts(args.name)}
        finally:
            eco.close()
        print(json.dumps({"command": "ecosystem", "result": result},
                         indent=1, default=str))
        return 0

    if args.cmd == "index":
        idx = index_mod.Indexer(root)
        stats = idx.build(full=args.full)
        idx.close()
        print(json.dumps({"command": "index", "result": stats}, indent=1))
        return 0

    svc = QueryService(root)
    try:
        if args.cmd != "status":
            pass
        fn = {"status": svc.repo_status, "modules": lambda: svc.modules(args.depth),
              "dialects": svc.dialects,
              "passes": lambda: svc.passes(args.query), "pass": lambda: svc.get_pass(args.name),
              "pipelines": svc.pipelines, "pipeline": lambda: svc.get_pipeline(args.name, brief=args.brief),
              "symbol": lambda: svc.find_symbol(args.name),
              "references": lambda: svc.get_references(args.name),
              "tests": lambda: svc.get_tests(args.name),
              "changed": lambda: svc.get_changes(args.base),
              "evidence": lambda: svc.get_evidence(args.ident),
              "pattern-owner": lambda: svc.pattern_owner(args.name),
              "pipeline-builder": lambda: svc.pipeline_builder(args.name),
              "attribute": lambda: svc.get_attribute(args.name),
              "attribute-provenance": lambda: svc.attribute_provenance(args.name),
              "pipeline-composition": lambda: svc.pipeline_composition(args.name),
              "dialect-transition": lambda: svc.dialect_transition(args.name),
              "semantic-contract": lambda: svc.semantic_contract(args.name),
              "boundary": lambda: svc.boundary(args.name),
              "pass-intent": lambda: svc.pass_intent(args.name),
              "pass-constraints": lambda: svc.pass_constraints(args.name)}[args.cmd]
        result = fn()
    finally:
        svc.close()



    stale = None
    svc2 = QueryService(root)
    try:
        stale = svc2._index_info()
    finally:
        svc2.close()
    print(json.dumps({"command": args.cmd,
                      "index": {k: stale[k] for k in ("head", "branch", "stale")},
                      "result": result}, indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())