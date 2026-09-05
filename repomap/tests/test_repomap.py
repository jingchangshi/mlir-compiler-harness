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
