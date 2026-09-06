"""Phase 20 adapter contract: feedback schema and documented CLI surface."""
import inspect
import io
import json
import os
import re
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stdout

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from mlir_repomap import cli  # noqa: E402
from mlir_repomap.feedback import validate_feedback  # noqa: E402
from mlir_repomap.index import Indexer  # noqa: E402


ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
ADAPTER = os.path.join(ROOT, "adapters", "compiler-dev")
COMMANDS = ("review", "finding-impact", "pipeline-stages", "evidence")


def _valid_feedback():
    return {"feedback": {
        "schema_version": 1,
        "created_at": "2026-09-06",
        "task": {"kind": "compiler-review", "target": "pass:hfusion-merge-vf"},
        "query": {"command": "review", "args": {"name": "MergeVecScope"}},
        "observation": "仍需手工确认 verifier 的控制流锚点。",
        "manual_source_search": {"performed": True, "reason": "定位 verifier。"},
        "possible_gap": {"category": "evidence-location",
                         "statement": "可能缺少 verifier location query。"},
        "evidence": [{"file": "lib/MergeVecScope.cpp", "lines": "1422"}],
        "sensitivity": {"contains_sensitive_content": False},
    }}


class FeedbackSchemaTest(unittest.TestCase):
    def test_usage_observation_is_valid_feedback(self):
        self.assertEqual(validate_feedback(_valid_feedback()), [])

    def test_only_adapter_queries_are_allowed(self):
        data = _valid_feedback()
        data["feedback"]["query"]["command"] = "pass"
        self.assertTrue(any("query.command" in error
                            for error in validate_feedback(data)))

    def test_sensitive_feedback_is_rejected(self):
        data = _valid_feedback()
        data["feedback"]["sensitivity"]["contains_sensitive_content"] = True
        self.assertTrue(any("redact" in error for error in validate_feedback(data)))

    def test_documented_feedback_example_validates(self):
        with open(os.path.join(ADAPTER, "feedback-schema.md"), encoding="utf-8") as fh:
            schema = fh.read()
        match = re.search(r"```json\n(.*?)\n```", schema, re.DOTALL)
        self.assertIsNotNone(match)
        self.assertEqual(validate_feedback(json.loads(match.group(1))), [])


class DocumentationConsistencyTest(unittest.TestCase):
    def test_contract_commands_match_the_cli_parser(self):
        with open(os.path.join(ADAPTER, "query-contract.md"), encoding="utf-8") as fh:
            contract = fh.read()
        parser_source = inspect.getsource(cli.main)
        for command in COMMANDS:
            self.assertIn(f"`mlir-repomap {command}", contract)
            self.assertIn(f'sub.add_parser("{command}")', parser_source)

    def test_review_keeps_the_stable_index_envelope(self):
        temporary = tempfile.mkdtemp()
        try:
            index = Indexer(temporary)
            index.build(full=True)
            index.close()
            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(cli.main(["--repo", temporary, "review", "missing"]), 0)
            envelope = json.loads(output.getvalue())
            self.assertEqual(envelope["command"], "review")
            self.assertEqual(set(envelope["index"]), {"head", "branch", "stale"})
        finally:
            shutil.rmtree(temporary)

    def test_feedback_schema_keeps_feedback_out_of_graph_and_findings(self):
        with open(os.path.join(ADAPTER, "feedback-schema.md"), encoding="utf-8") as fh:
            schema = fh.read()
        self.assertIn("不是 finding", schema)
        self.assertIn("绝不进入 graph", schema)
        self.assertIn("contains_sensitive_content", schema)


if __name__ == "__main__":
    unittest.main()
