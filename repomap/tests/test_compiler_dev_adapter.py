"""Phase 20/21 adapter contract：feedback schema 与已文档化的 CLI surface。"""
import inspect
import io
import json
import os
import re
import shutil
import sys
import tempfile
import unittest
from copy import deepcopy
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


def _valid_v2_feedback(kind="query-sufficient"):
    query = {"command": "review", "args": {"name": "MergeVecScope"}}
    return {"feedback": {
        "schema_version": 2,
        "created_at": "2026-09-07",
        "origin": "automatic",
        "observation_kind": kind,
        "task": {
            "kind": "compiler-review",
            "target": "pass:hfusion-merge-vf",
            "classification": {"confidence": "high", "source": "heuristic"},
        },
        "query": None if kind == "adoption-missed" else query,
        "route": {"knowledge_expected": True, "kind": "pass-review", "confidence": "high"},
        "usage": {
            "compiler_knowledge_calls": 0 if kind == "adoption-missed" else 1,
            "knowledge_commands": {} if kind == "adoption-missed" else {"review": 1},
            "first_knowledge_step": 3,
        },
        "operational": {"duration_ms": 3400},
        "observation": "记录最小、非敏感的知识系统使用观察。",
        "manual_source_search": {"performed": False},
        "possible_gap": None,
        "evidence": [],
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
        examples = re.findall(r"```json\n(.*?)\n```", schema, re.DOTALL)
        self.assertGreaterEqual(len(examples), 2)
        self.assertEqual(validate_feedback(json.loads(examples[0])), [])
        self.assertEqual(validate_feedback(json.loads(examples[1])), [])

    def test_v2_all_observation_kinds_are_valid(self):
        for kind in ("query-sufficient", "query-insufficient", "adoption-missed",
                     "query-operational"):
            self.assertEqual(validate_feedback(_valid_v2_feedback(kind)), [], kind)

    def test_v2_adoption_missed_requires_expected_route_and_zero_calls(self):
        data = _valid_v2_feedback("adoption-missed")
        data["feedback"]["route"]["knowledge_expected"] = False
        self.assertTrue(any("knowledge_expected" in error
                            for error in validate_feedback(data)))
        data = _valid_v2_feedback("adoption-missed")
        data["feedback"]["usage"]["compiler_knowledge_calls"] = 1
        self.assertTrue(any("compiler_knowledge_calls" in error
                            for error in validate_feedback(data)))
        data = _valid_v2_feedback("adoption-missed")
        data["feedback"]["query"] = {"command": "review", "args": {}}
        self.assertTrue(any("query: null" in error for error in validate_feedback(data)))

    def test_v2_query_observations_require_query(self):
        data = _valid_v2_feedback("query-insufficient")
        data["feedback"].pop("query")
        self.assertTrue(any("requires query" in error for error in validate_feedback(data)))

    def test_v2_rejects_unknown_sensitive_and_invalid_classification_fields(self):
        data = _valid_v2_feedback()
        data["feedback"]["prompt"] = "不得保存"
        self.assertTrue(any("unknown field: prompt" in error
                            for error in validate_feedback(data)))
        data = _valid_v2_feedback()
        data["feedback"]["sensitivity"]["contains_sensitive_content"] = True
        self.assertTrue(any("redact" in error for error in validate_feedback(data)))
        data = _valid_v2_feedback()
        data["feedback"]["task"]["classification"]["confidence"] = "certain"
        self.assertTrue(any("classification.confidence" in error
                            for error in validate_feedback(data)))

    def test_v2_rejects_malformed_usage_and_unknown_schema(self):
        data = _valid_v2_feedback()
        data["feedback"]["usage"]["compiler_knowledge_calls"] = True
        self.assertTrue(any("usage.compiler_knowledge_calls" in error
                            for error in validate_feedback(data)))
        data = deepcopy(_valid_v2_feedback())
        data["feedback"]["schema_version"] = 3
        self.assertTrue(any("schema_version" in error for error in validate_feedback(data)))


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
        self.assertIn("不是 compiler finding", schema)
        self.assertIn("不会进入 graph", schema)
        self.assertIn("contains_sensitive_content", schema)


if __name__ == "__main__":
    unittest.main()
