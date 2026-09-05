"""Finding artifact tests: YAML-subset parsing, lifecycle validation, git drift."""
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from mlir_repomap.findings import (FindingService, YamlSubsetError,  # noqa: E402
                                   parse_finding_text, validate_finding)

GOOD = """\
finding:
  id: T-001
  category: correctness
  pass: simple-fold
  statement: >-
    The pass assumes X but nothing enforces it.
  evidence:
    - file: lib/SimpleFold.cpp
      lines: 10-20
      snippet: "return failure();"
  reasoning: >-
    Agent reasoning: the contract has no guard.
  status: open
  created_at: 2026-09-05
  review:
    baseline_commit: will-be-replaced
"""


def _write(tmp, name, text):
    path = os.path.join(tmp, name)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)
    return path


class ParseValidateTest(unittest.TestCase):
    def test_good_finding_roundtrip(self):
        data = parse_finding_text(GOOD)
        self.assertEqual(validate_finding(data), [])
        f = data["finding"]
        self.assertEqual(f["id"], "T-001")
        self.assertEqual(f["evidence"][0]["lines"], "10-20")
        self.assertEqual(f["statement"], "The pass assumes X but nothing enforces it.")

    def test_block_scalar_keeps_newlines(self):
        text = GOOD.replace(
            "  statement: >-\n    The pass assumes X but nothing enforces it.\n",
            "  statement: |\n    Line one of the claim.\n    Line two of the claim.\n")
        f = parse_finding_text(text)["finding"]
        self.assertEqual(f["statement"],
                         "Line one of the claim.\nLine two of the claim.")

    def test_flow_style_rejected(self):
        with self.assertRaises(YamlSubsetError):
            parse_finding_text("finding:\n  evidence: [a, b]\n")

    def test_missing_required_field(self):
        bad = GOOD.replace("  status: open\n", "")
        errors = validate_finding(parse_finding_text(bad))
        self.assertTrue(any("status" in e for e in errors))

    def test_bad_category(self):
        bad = GOOD.replace("category: correctness", "category: bug")
        self.assertTrue(any("category" in e
                            for e in validate_finding(parse_finding_text(bad))))

    def test_resolved_requires_history_reason(self):
        resolved = GOOD.replace("  status: open\n", "  status: resolved\n") + \
            "  history:\n    - status: resolved\n      at: 2026-09-05\n"
        errors = validate_finding(parse_finding_text(resolved))
        self.assertTrue(any("reason" in e for e in errors))

    def test_superseded_requires_superseded_by(self):
        sup = GOOD.replace("  status: open\n", "  status: superseded\n")
        errors = validate_finding(parse_finding_text(sup))
        self.assertTrue(any("superseded_by" in e for e in errors))

    def test_history_transition_valid(self):
        hist = GOOD + ("  history:\n    - status: acknowledged\n      at: 2026-09-06\n"
                       "      reason: triaged by pass owner\n"
                       "      reference: review-meeting-notes\n")
        self.assertEqual(validate_finding(parse_finding_text(hist)), [])


class DriftTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.repo = os.path.join(self.tmp, "repo")
        os.makedirs(self.repo)
        self.findings = os.path.join(self.tmp, "findings")
        os.makedirs(self.findings)
        self._git("init", "-q")
        self._git("config", "user.email", "t@t")
        self._git("config", "user.name", "t")
        with open(os.path.join(self.repo, "pass.cpp"), "w") as fh:
            fh.write("void run() {\n  return failure();\n}\n")
        self._git("add", "-A")
        self._git("commit", "-q", "-m", "base")
        self.base = subprocess.run(["git", "-C", self.repo, "rev-parse", "HEAD"],
                                   capture_output=True, text=True).stdout.strip()
        text = GOOD.replace("will-be-replaced", self.base)
        text = text.replace("lib/SimpleFold.cpp", "pass.cpp")
        _write(self.findings, "T-001.yaml", text)

    def tearDown(self):
        shutil.rmtree(self.tmp)

    def _git(self, *args):
        subprocess.run(["git", "-C", self.repo, *args], capture_output=True,
                       check=True)

    def test_no_drift(self):
        res = FindingService(self.findings, repo=self.repo).check()
        self.assertEqual(res["summary"]["needs_review"], 0)
        self.assertEqual(res["results"][0]["snippets_verified"], 1)

    def test_commit_on_evidence_file_needs_review(self):
        with open(os.path.join(self.repo, "pass.cpp"), "w") as fh:
            fh.write("void run() {\n  return failure();\n  // more code\n}\n")
        self._git("add", "-A")
        self._git("commit", "-q", "-m", "touch pass file")
        res = FindingService(self.findings, repo=self.repo).check()
        r = res["results"][0]
        self.assertTrue(r["needs_review"])
        self.assertEqual(r["affected_by"][0]["subject"], "touch pass file")
        self.assertIn("possibly affected by commit", r["verdict"])

    def test_snippet_gone_is_evidence_changed(self):
        with open(os.path.join(self.repo, "pass.cpp"), "w") as fh:
            fh.write("void run() {\n  return failure();\n")
        os.rename(os.path.join(self.repo, "pass.cpp"),
                  os.path.join(self.repo, "pass2.cpp"))
        self._git("add", "-A")
        self._git("commit", "-q", "-m", "replace guard with legality check")
        res = FindingService(self.findings, repo=self.repo).check()
        r = res["results"][0]
        self.assertTrue(r["evidence_changed"])
        self.assertTrue(r["needs_review"])
        self.assertIn("evidence changed", r["verdict"])

    def test_no_baseline_unchecked(self):
        text = GOOD.replace("will-be-replaced", "0000000").replace(
            "lib/SimpleFold.cpp", "pass.cpp")
        _write(self.findings, "T-002.yaml", text)
        res = FindingService(self.findings, repo=self.repo).check()
        self.assertEqual(res["summary"]["unchecked"], 1)
        self.assertIn("no baseline", res["results"][1]["reason"])

    def test_list_and_show(self):
        svc = FindingService(self.findings, repo=self.repo)
        listing = svc.list(pass_name="simple-fold")
        self.assertEqual(listing["count"], 1)
        self.assertEqual(svc.show("t-001")["finding"]["id"], "T-001")


if __name__ == "__main__":
    unittest.main()
