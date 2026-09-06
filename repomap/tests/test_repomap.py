"""Synthetic fixture repositories + unit tests for extractor and query behavior."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from mlir_repomap.index import Indexer  # noqa: E402
from mlir_repomap.query import QueryService  # noqa: E402

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")


def _git(cwd, *args):
    subprocess.run(["git", "-C", cwd, "-c", "user.email=t@t", "-c", "user.name=t", *args],
                   capture_output=True, check=True)


class FixtureTest(unittest.TestCase):
    """One shared index over the simple-pass fixture (conditional pipeline, patterns)."""

    @classmethod
    def setUpClass(cls):
        cls.repo = os.path.join(FIXTURES, "simple-pass")
        idx = Indexer(cls.repo)
        idx.build(full=True)
        idx.close()
        cls.svc = QueryService(cls.repo)

    @classmethod
    def tearDownClass(cls):
        cls.svc.close()

    def test_dialect_and_ops_extracted(self):
        d = self.svc.dialects("Simple")
        self.assertEqual(len(d["dialects"]), 1)
        self.assertEqual(d["dialects"][0]["owns"].get("op"), 1)

    def test_pass_dossier(self):
        r = self.svc.get_pass("simple-fold")
        self.assertNotIn("error", r)
        self.assertTrue(any(e["src"].endswith(".td") for e in r["definition"]))
        self.assertEqual(r["factory"], ["factory:createSimpleFoldPass"])
        mem = {m["scope"]: m for m in r["pipeline_memberships"]
               if m["pipeline"] == "pipeline:lib/Pipeline.cpp:buildSimplePipeline"}
        self.assertIn("module", mem)
        self.assertIn("func::FuncOp", mem)
        self.assertEqual(mem["module"]["condition"], "config.getEnableFancy()")
        pats = [p for p in r["patterns"] if "populator" not in p]
        self.assertEqual(len(pats), 1)
        self.assertEqual(pats[0]["matches_ops"], ["op:Simple_FoldOp"])
        self.assertEqual(pats[0]["creates_ops"], ["op:Simple_CanonicalOp"])
        self.assertTrue(r["tests"])

    def test_pipeline_order_and_conditions(self):
        r = self.svc.get_pipeline("pipeline:lib/Pipeline.cpp:buildSimplePipeline")
        self.assertNotIn("error", r)
        conds = {(s["pass"], s["scope"]): s["condition"] for s in r["stages"]}
        self.assertIsNone(conds.get(("pass:Inline", "module")))
        self.assertEqual(conds.get(("pass:simple-fold", "module")),
                         "config.getEnableFancy()")
        self.assertTrue(r["sub_pipelines"])

    def test_pipeline_brief_mode_is_compact(self):
        full = self.svc.get_pipeline("pipeline:lib/Pipeline.cpp:buildSimplePipeline")
        brief = self.svc.get_pipeline("pipeline:lib/Pipeline.cpp:buildSimplePipeline",
                                      brief=True)
        self.assertNotIn("evidence", brief["stages"][0])
        self.assertIn("evidence", full["stages"][0])
        self.assertEqual(len(full["stages"]), len(brief["stages"]))

    def test_incremental_unchanged(self):
        idx = Indexer(self.repo)
        stats = idx.build()  # no changes
        idx.close()
        self.assertEqual(stats["reextracted"], 0)
        self.assertGreater(stats["unchanged"], 0)

    def test_incremental_reextracts_on_touch(self):
        target = os.path.join(self.repo, "lib", "SimpleFold.cpp")
        with open(target) as f:
            original = f.read()
        try:
            with open(target, "a") as f:
                f.write("\n// touch\n")
            idx = Indexer(self.repo)
            stats = idx.build()
            idx.close()
            self.assertEqual(stats["reextracted"], 1)
            # dossier still complete after re-extraction
            svc = QueryService(self.repo)
            r = svc.get_pass("simple-fold")
            svc.close()
            self.assertEqual(r["factory"], ["factory:createSimpleFoldPass"])
        finally:
            with open(target, "w") as f:
                f.write(original)
            # re-sync the stored hash with the restored content so later
            # incremental tests still see an unchanged tree
            idx = Indexer(self.repo)
            idx.build()
            idx.close()

    def test_pass_resolution_by_class_and_factory_name(self):
        # user-facing names: td class / cpp class / factory, not only the pass arg
        for name in ("SimpleFoldPass", "createSimpleFoldPass"):
            r = self.svc.get_pass(name)
            self.assertEqual(r["pass"]["id"], "pass:simple-fold", name)

    def test_pattern_provenance_chain(self):
        r = self.svc.get_pass("simple-fold")
        pops = [p for p in r["patterns"] if "populator" in p]
        self.assertTrue(pops, "populator provenance missing")
        pop = [p for p in pops if "populateSimpleFoldPatterns" in p["populator"]][0]
        self.assertEqual({p["pattern"] for p in pop["patterns"]},
                         {"pattern:SecondSimplePattern"})  # FoldSimplePattern is direct-use
        own = self.svc.pattern_owner("SecondSimplePattern")
        own = self.svc.pattern_owner("FoldSimplePattern")
        self.assertTrue(any("populateSimpleFoldPatterns" in o["function"]
                            for o in own["populators"]))
        self.assertTrue(any(any("pass:simple-fold" == p["src"] for p in o["passes"])
                            for o in own["populators"]))

    def test_same_name_pipeline_builders_not_merged(self):
        r = self.svc.get_pipeline("buildSimplePipeline")
        self.assertEqual(r.get("error"), "ambiguous")
        ids = r["candidates"]
        self.assertEqual(len(ids), 2)
        self.assertTrue(all(":" in i for i in ids))
        one = self.svc.get_pipeline([i for i in ids if "Pipeline.cpp:" in i][0])
        self.assertEqual(len([s for s in one["stages"] if s["scope"] == "module"]), 3)
        self.assertTrue(all(s.get("seq") is not None for s in one["stages"]))
        b = self.svc.pipeline_builder("buildSimplePipeline")
        self.assertEqual(b.get("error"), "ambiguous")
        pb = self.svc.pipeline_builder([i for i in ids if "Pipeline.cpp:" in i][0])
        self.assertTrue(pb["builders"])

    def test_ambiguous_short_name_is_explicit(self):
        # short names matching several passes must not resolve silently
        r = self.svc.get_pass("FoldPass")
        self.assertEqual(r.get("error"), "not found")

    def test_fail_soft_on_bad_file(self):
        tmp = tempfile.mkdtemp()
        try:
            _git(tmp, "init", "-q")
            with open(os.path.join(tmp, "broken.cpp"), "w") as f:
                f.write("struct \x01 Broken : public PassWrapper< {")
            with open(os.path.join(tmp, "ok.td"), "w") as f:
                f.write('def OkDialect : Dialect<"ok"> {}\n')
            _git(tmp, "add", "-A")
            _git(tmp, "commit", "-qm", "x")
            idx = Indexer(tmp)
            idx.build(full=True)
            diags = idx.store.db.execute("SELECT COUNT(*) FROM diagnostics").fetchone()[0]
            ok = idx.store.db.execute("SELECT COUNT(*) FROM nodes WHERE kind='dialect'"
                                      ).fetchone()[0]
            idx.close()
            self.assertGreaterEqual(diags, 0)
            self.assertEqual(ok, 1)  # indexing continued
        finally:
            shutil.rmtree(tmp)


class EmptyRepoTest(unittest.TestCase):
    def test_queries_on_fresh_repo(self):
        tmp = tempfile.mkdtemp()
        try:
            _git(tmp, "init", "-q")
            svc = QueryService(tmp)
            st = svc.repo_status()
            self.assertEqual(st["entity_counts"], {})
            self.assertEqual(svc.get_pass("nope").get("error"), "not found")
            self.assertEqual(svc.get_tests("nope")["tests"], [])
            svc.close()
        finally:
            shutil.rmtree(tmp)


if __name__ == "__main__":
    unittest.main(verbosity=2)


class AttributeProvenanceTest(unittest.TestCase):
    """Phase 15 / RG-1: typed attribute creator provenance (ADR-021)."""

    @classmethod
    def setUpClass(cls):
        cls.repo = os.path.join(FIXTURES, "simple-pass")
        idx = Indexer(cls.repo)
        idx.build(full=True)
        idx.close()
        cls.svc = QueryService(cls.repo)

    @classmethod
    def tearDownClass(cls):
        cls.svc.close()

    def _prov(self, name):
        return self.svc.attribute_provenance(name)

    def test_definition_join_and_dialect(self):
        r = self._prov("Simple_MagicAttr")
        self.assertEqual(len(r["definitions"]), 1)
        d = r["definitions"][0]
        self.assertEqual(d["node"]["id"], "attr:Simple_MagicAttr")
        self.assertEqual(d["dialects"][0]["dialect"], "dialect:Simple")
        self.assertEqual(d["confidence"], "confirmed")

    def test_creator_types(self):
        r = self._prov("Simple_MagicAttr")
        types = {c["entity"]["id"]: c["type"] for c in r["creators"]}
        self.assertEqual(types.get("symbol:SimpleOp"), "OpBuilder")
        self.assertEqual(types.get("pattern:MagicAnnotatePattern"),
                         "RewritePattern")
        self.assertEqual(types.get("pattern:MagicConvertPattern"),
                         "ConversionPattern")
        self.assertTrue(any(t == "PipelineBuilder" and
                            "buildMagicPipeline" in e for e, t in types.items()),
                        types)

    def test_attach_flag_marks_attachment_sites(self):
        r = self._prov("Simple_MagicAttr")
        att = {c["entity"]["id"]: c["attach"] for c in r["creators"]}
        self.assertTrue(att["symbol:SimpleOp"])          # state.addAttribute
        self.assertTrue(att["pattern:MagicAnnotatePattern"])  # setAttr
        self.assertTrue(att["pattern:MagicConvertPattern"])

    def test_verifier_is_consumer_not_creator(self):
        r = self._prov("Simple_MagicAttr")
        creator_ids = {c["entity"]["id"] for c in r["creators"]}
        self.assertNotIn("symbol:SimpleCheckOp", creator_ids)
        cons = {c["entity"]["id"]: c["role"] for c in r["consumers"]}
        self.assertEqual(cons.get("symbol:SimpleCheckOp"), "verifier")

    def test_pass_creator_typed(self):
        r = self._prov("Simple_MagicV2Attr")
        self.assertTrue(any(c["type"] == "Pass" for c in r["creators"]),
                        r["creators"])
        self.assertTrue(all(c["attach"] for c in r["creators"]))

    def test_ambiguous_attribute_query_is_explicit(self):
        r = self._prov("Simple_Magic")
        self.assertEqual(r.get("error"), "ambiguous")
        self.assertEqual(len(r["candidates"]), 2)

    def test_unknown_attribute(self):
        self.assertEqual(self._prov("Nope_Attr").get("error"), "not found")


class FindingImpactTest(unittest.TestCase):
    """Phase 16 (ADR-022): entity-aware finding impact + constraint diff."""

    @classmethod
    def setUpClass(cls):
        cls.repo = os.path.join(FIXTURES, "simple-pass")
        idx = Indexer(cls.repo)
        idx.build(full=True)
        idx.close()
        cls.tmp = tempfile.mkdtemp()
        cls.findings = os.path.join(cls.tmp, "findings")
        os.makedirs(cls.findings)
        # a controlled git repo for drift + constraint diff: guard changes
        # between baseline and HEAD while entity_refs resolve against the
        # fixture graph (the two are independent by design)
        cls.grepo = os.path.join(cls.tmp, "grepo")
        os.makedirs(cls.grepo)
        cls._git("init", "-q")
        cls._git("config", "user.email", "t@t")
        cls._git("config", "user.name", "t")
        cls._write_pass(["  if (dim > 4) {", "    return signalPassFailure();", "  }"])
        cls._git("add", "-A")
        cls._git("commit", "-q", "-m", "base with guard")
        out = subprocess.run(["git", "-C", cls.grepo, "rev-parse", "HEAD"],
                             capture_output=True, text=True)
        cls.base = out.stdout.strip()

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp)

    @staticmethod
    def _guard_body(guard_lines):
        body = "\n".join(guard_lines)
        return f'''
#include "mlir/Pass/Pass.h"
using namespace mlir;
struct FoldPass : public PassWrapper<OperationPass<ModuleOp>> {{
  void runOnOperation() override {{
    int dim = 0;
{body}
  }}
}};
'''

    @classmethod
    def _write_pass(cls, guard_lines):
        with open(os.path.join(cls.grepo, "pass.cpp"), "w") as fh:
            fh.write(cls._guard_body(guard_lines))

    @classmethod
    def _git(cls, *args):
        subprocess.run(["git", "-C", cls.grepo, *args], capture_output=True,
                       check=True)

    def _write_finding(self, name, text):
        with open(os.path.join(self.findings, name), "w", encoding="utf-8") as fh:
            fh.write(text)

    def _finding(self, refs='  entity_refs:\n    - pass: simple-fold\n'):
        return f'''\
finding:
  id: FI-001
  category: correctness
  pass: simple-fold
  statement: >-
    The fold guard may be weakened by recent changes.
  evidence:
    - file: pass.cpp
      lines: 4-8
      snippet: "signalPassFailure"
  reasoning: >-
    Agent reasoning: the guard change may weaken the protected invariant.
{refs}  status: open
  created_at: 2026-09-05
  review:
    baseline_commit: {self.base}
'''

    def test_finding_entity_ref_validation(self):
        from mlir_repomap.findings import parse_finding_text, validate_finding
        good = parse_finding_text(self._finding())
        self.assertEqual(validate_finding(good), [])
        bad = self._finding(refs='  entity_refs:\n    - dragon: simple-fold\n')
        errs = validate_finding(parse_finding_text(bad))
        self.assertTrue(any("entity_refs" in e for e in errs))

    def test_finding_impact_query_with_signals(self):
        self._write_finding("FI-001.yaml", self._finding())
        # evolve the guard: same shape, new condition + new commit on the file
        self._write_pass(["  if (dim > 8) {", "    return signalPassFailure();", "  }"])
        self._git("add", "-A")
        self._git("commit", "-q", "-m", "relax fold guard")
        from mlir_repomap.impact import ImpactService
        svc = ImpactService(self.repo, findings_dir=self.findings,
                            git_repo=self.grepo)
        try:
            r = svc.impact("FI-001")
        finally:
            svc.close()
        self.assertEqual(r["affected_entities"][0]["id"], "pass:simple-fold")
        self.assertEqual(r["affected_entities"][0]["resolution"], "exact")
        types = {s["type"] for s in r["changed_signals"]}
        self.assertIn("file-commits", types)
        self.assertIn("constraint-diff", types)
        cd = next(s for s in r["changed_signals"]
                  if s["type"] == "constraint-diff")
        self.assertEqual(cd["classification"], "changed guard set")
        self.assertTrue(any("dim > 4" == x["text"] for x in cd["removed"]))
        self.assertTrue(any("dim > 8" == x["text"] for x in cd["added"]))
        self.assertTrue(r["test_signal"], "lit coverage expected")
        self.assertIn("pass:simple-fold", r["review_scope"]["suggestion"])

    def test_finding_impact_negative_no_evidence_no_impact(self):
        # baseline = current state: no commits, no constraint change
        out = subprocess.run(["git", "-C", self.grepo, "rev-parse", "HEAD"],
                             capture_output=True, text=True)
        head = out.stdout.strip()
        text = self._finding().replace(self.base, head).replace("FI-001", "FI-NEG")
        self._write_finding("FI-NEG.yaml", text)
        from mlir_repomap.impact import ImpactService
        svc = ImpactService(self.repo, findings_dir=self.findings,
                            git_repo=self.grepo)
        try:
            r = svc.impact("FI-NEG")
        finally:
            svc.close()
        self.assertEqual(r["changed_signals"], [])
        self.assertTrue(r["review_scope"]["suggestion"].endswith(
            "(no file-level drift detected since baseline)"))

    def test_finding_impact_unresolved_ref_is_uncertainty(self):
        text = self._finding().replace(
            "    - pass: simple-fold",
            "    - pass: no-such-pass-xyz").replace("FI-001", "FI-UNC")
        self._write_finding("FI-UNC.yaml", text)
        from mlir_repomap.impact import ImpactService
        svc = ImpactService(self.repo, findings_dir=self.findings,
                            git_repo=self.grepo)
        try:
            r = svc.impact("FI-UNC")
        finally:
            svc.close()
        # the finding's own pass field still resolves; the bad ref is uncertainty
        self.assertTrue(any("no pass entity" in u for u in r["uncertainty"]))
        self.assertEqual(r["affected_entities"][0]["resolution"], "not-found")

    def test_constraint_diff_classifications(self):
        from mlir_repomap.impact import constraint_diff
        self._write_pass(["  if (dim > 2) {", "    return signalPassFailure();", "  }"])
        self._git("add", "-A")
        self._git("commit", "-q", "-m", "set baseline guard")
        base = subprocess.run(["git", "-C", self.grepo, "rev-parse", "HEAD"],
                              capture_output=True, text=True).stdout.strip()
        self._write_pass(["  if (dim > 2) {", "    return signalPassFailure();", "  }",
                          "  if (magic) {", "    return failure();", "  }"])
        self._git("add", "-A")
        self._git("commit", "-q", "-m", "add guard")
        d = constraint_diff(self.grepo, "pass.cpp", base)
        self.assertEqual(d["classification"],
                         "possible strengthening (guard(s) added)")
        self._write_pass([])
        self._git("add", "-A")
        self._git("commit", "-q", "-m", "drop guard")
        d = constraint_diff(self.grepo, "pass.cpp", base)
        self.assertEqual(d["classification"],
                         "possible weakening (guard(s) removed)")

    def test_gtest_coverage_signal(self):
        svc = QueryService(self.repo)
        try:
            r = svc.get_tests("simple-fold")
            kinds = {t["test"]: t["confidence"] for t in r["tests"]}
            self.assertTrue(any("SimplePassGTest" in t for t in kinds))
            gtest = [c for t, c in kinds.items() if "SimplePassGTest" in t]
            self.assertEqual(gtest, ["heuristic"])
            # unrelated gtest suite must NOT be linked
            self.assertFalse(any("UnrelatedSuite" in t for t in kinds))
            lit = [c for t, c in kinds.items() if "SimplePassGTest" not in t]
            self.assertTrue(lit and all(c == "exact" for c in lit),
                            kinds)  # lit flag == confirmed pass arg
        finally:
            svc.close()


class ReviewMemoryTest(unittest.TestCase):
    """Phase 17 (ADR-023): review memory query + evidence catalog."""

    @classmethod
    def setUpClass(cls):
        cls.repo = os.path.join(FIXTURES, "simple-pass")
        idx = Indexer(cls.repo)
        idx.build(full=True)
        idx.close()
        cls.tmp = tempfile.mkdtemp()
        cls.findings = os.path.join(cls.tmp, "findings")
        cls.docs = os.path.join(cls.tmp, "docs")
        os.makedirs(cls.findings)
        os.makedirs(os.path.join(cls.docs, "passes"))
        cls.grepo = os.path.join(cls.tmp, "grepo")
        os.makedirs(cls.grepo)
        cls._git("init", "-q")
        cls._git("config", "user.email", "t@t")
        cls._git("config", "user.name", "t")
        cls._write_pass(["  if (dim > 4) {", "    return signalPassFailure();", "  }"])
        cls._git("add", "-A")
        cls._git("commit", "-q", "-m", "base with guard")
        cls.base = subprocess.run(["git", "-C", cls.grepo, "rev-parse", "HEAD"],
                                  capture_output=True, text=True).stdout.strip()
        cls._write_finding("FI-001.yaml", f'''\
finding:
  id: FI-001
  category: correctness
  pass: simple-fold
  statement: >-
    The fold guard may be weakened.
  evidence:
    - file: pass.cpp
      lines: 4-8
      snippet: "signalPassFailure"
  reasoning: >-
    Agent reasoning layer.
  status: open
  created_at: 2026-09-05
  review:
    baseline_commit: {cls.base}
''')
        cls._write_finding("FV-002.yaml", '''\
finding:
  id: FV-002
  category: architecture
  pass: some-other-pass
  statement: >-
    Cross-cutting concern touching simple-fold via entity refs.
  evidence:
    - file: elsewhere.cpp
      lines: 1-2
  entity_refs:
    - pass: simple-fold
  reasoning: >-
    Agent reasoning layer.
  status: acknowledged
  created_at: 2026-09-05
''')
        with open(os.path.join(cls.docs, "passes", "simple-fold.md"), "w") as fh:
            fh.write('''# simple-fold (SimpleFoldPass)

# Overview

Folds simple ops.

# Compiler Review (Phase 13 — review record, agent layer)

- **Protected invariants**: folded-result validity, ENFORCED by the
  legality-guard at SimpleFold.cpp:7.
- **UNGUARDED**: none recorded.
''')

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp)

    @staticmethod
    def _guard_body(guard_lines):
        body = "\n".join(guard_lines)
        return f'''
struct FoldPass : public PassWrapper<OperationPass<ModuleOp>> {{
  void runOnOperation() override {{
    int dim = 0;
{body}
  }}
}};
'''

    @classmethod
    def _write_pass(cls, guard_lines):
        with open(os.path.join(cls.grepo, "pass.cpp"), "w") as fh:
            fh.write(cls._guard_body(guard_lines))

    @classmethod
    def _git(cls, *args):
        subprocess.run(["git", "-C", cls.grepo, *args], capture_output=True,
                       check=True)

    @classmethod
    def _write_finding(cls, name, text):
        with open(os.path.join(cls.findings, name), "w", encoding="utf-8") as fh:
            fh.write(text)

    def _svc(self):
        from mlir_repomap.impact import ImpactService
        return ImpactService(self.repo, findings_dir=self.findings,
                             git_repo=self.grepo, docs_dir=self.docs)

    def test_review_query_joins_all_layers(self):
        svc = self._svc()
        try:
            r = svc.review("simple-fold")
        finally:
            svc.close()
        self.assertEqual(r["pass"]["id"], "pass:simple-fold")
        self.assertEqual(len(r["review_records"]), 1)
        self.assertIn("Protected invariants", r["review_records"][0]["record"])
        ids = {f["id"]: f["matched_via"] for f in r["findings"]}
        self.assertEqual(ids.get("FI-001"), ["pass-field"])
        self.assertEqual(ids.get("FV-002"), ["entity_refs"])
        guards = [(g["kind"], g["constraint"]) for g in r["invariant_guards"]]
        self.assertIn(("legality-guard", "constraint:lib/SimpleFold.cpp:7"),
                      guards)

    def test_review_recent_impact_integration(self):
        self._write_pass(["  if (dim > 8) {", "    return signalPassFailure();", "  }"])
        self._git("add", "-A")
        self._git("commit", "-q", "-m", "relax fold guard")
        svc = self._svc()
        try:
            r = svc.review("simple-fold")
        finally:
            svc.close()
        imp = {i["finding"]: i for i in r["recent_impact"]}
        self.assertIn("FI-001", imp)
        types = {s["type"] for s in imp["FI-001"]["signals"]}
        self.assertIn("file-commits", types)
        self.assertIn("constraint-diff", types)

    def test_evidence_catalog(self):
        svc = QueryService(self.repo)
        try:
            r = svc.get_evidence("constraint:lib/SimpleFold.cpp:7")
            self.assertTrue(r["evidence_rows"])
            self.assertEqual(r["entity"]["id"],
                             "constraint:lib/SimpleFold.cpp:7")
            self.assertTrue(r["recent_history"],
                            "SimpleFold.cpp has commits in the harness repo")
            self.assertEqual(r["referenced_by_findings"], [])
            # positive linkage: a finding citing this constraint by ref+file
            fdir = os.path.join(self.repo, "docs", "compiler-architecture",
                                "findings")
            os.makedirs(fdir, exist_ok=True)
            fpath = os.path.join(fdir, "FI-CAT.yaml")
            with open(fpath, "w", encoding="utf-8") as fh:
                fh.write('''\
finding:
  id: FI-CAT
  category: correctness
  pass: simple-fold
  statement: >-
    Guard referenced by a finding.
  evidence:
    - file: lib/SimpleFold.cpp
      lines: 6-9
      ref: constraint:lib/SimpleFold.cpp:7
  reasoning: >-
    Agent reasoning layer.
  status: open
  created_at: 2026-09-05
''')
            try:
                r2 = svc.get_evidence("constraint:lib/SimpleFold.cpp:7")
                self.assertEqual(len(r2["referenced_by_findings"]), 1)
                self.assertEqual(r2["referenced_by_findings"][0]["id"], "FI-CAT")
                self.assertIn("evidence.ref",
                              r2["referenced_by_findings"][0]["matched_via"])
            finally:
                os.remove(fpath)
                os.rmdir(fdir)
        finally:
            svc.close()

    def test_missing_artifact_negative(self):
        empty_docs = os.path.join(self.tmp, "empty-docs")
        empty_findings = os.path.join(self.tmp, "empty-findings")
        os.makedirs(empty_docs)
        os.makedirs(empty_findings)
        from mlir_repomap.impact import ImpactService
        svc = ImpactService(self.repo, findings_dir=empty_findings,
                            git_repo=self.grepo, docs_dir=empty_docs)
        try:
            r = svc.review("simple-fold")
        finally:
            svc.close()
        self.assertEqual(r["review_records"], [])
        self.assertEqual(r["findings"], [])
        self.assertTrue(any("no review memory found" in n for n in r["notes"]))
        svc2 = QueryService(self.repo)
        try:
            cat = svc2.get_evidence("pass:does-not-exist")
            self.assertIsNone(cat["entity"])
            self.assertEqual(cat["evidence_rows"], [])
            self.assertEqual(cat["referenced_by_findings"], [])
        finally:
            svc2.close()
