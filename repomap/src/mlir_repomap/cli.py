"""Thin CLI frontend over QueryService (ADR-004: no business logic here)."""
import argparse
import json
import os
import sys


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

    args = ap.parse_args(argv)
    root = args.repo

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
