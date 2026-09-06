"""Validation for CompilerDev knowledge-system usage feedback.

Feedback records whether a consumer could use the deterministic query surface.  They
are intentionally outside the graph and are not compiler findings: they record a
possible retrieval or workflow gap, never a claim about compiler correctness.
"""

import re


QUERY_COMMANDS = ("review", "finding-impact", "pipeline-stages", "evidence")
TASK_KINDS = ("compiler-review", "bug-investigation", "pipeline-audit", "other")
GAP_CATEGORIES = ("query-coverage", "evidence-location", "workflow", "documentation",
                  "other")


def _error(errors, source, message):
    errors.append(f"{source}: {message}")


def _nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def _lines(value):
    return isinstance(value, int) and value > 0 or (
        isinstance(value, str) and bool(re.fullmatch(r"\d+(-\d+)?", value)))


def validate_feedback(data, source="<feedback>"):
    """Return schema errors for one feedback artifact; an empty list is valid.

    The validator is deliberately a small stdlib-only boundary.  It does not persist
    data, invoke an agent, or open an index, so feedback cannot become graph evidence
    or mutate a finding lifecycle.
    """
    errors = []
    if not isinstance(data, dict) or set(data) != {"feedback"}:
        _error(errors, source, "document must be a single top-level 'feedback' mapping")
        return errors
    feedback = data["feedback"]
    if not isinstance(feedback, dict):
        _error(errors, source, "'feedback' must be a mapping")
        return errors
    if feedback.get("schema_version") != 1:
        _error(errors, source, "schema_version must be 1")
    if not _nonempty(feedback.get("created_at")):
        _error(errors, source, "missing required field: created_at")

    task = feedback.get("task")
    if not isinstance(task, dict):
        _error(errors, source, "task must be a mapping")
    else:
        if task.get("kind") not in TASK_KINDS:
            _error(errors, source, f"task.kind must be one of {TASK_KINDS}")
        if not _nonempty(task.get("target")):
            _error(errors, source, "task.target must be a non-empty stable target")

    query = feedback.get("query")
    if not isinstance(query, dict):
        _error(errors, source, "query must be a mapping")
    else:
        if query.get("command") not in QUERY_COMMANDS:
            _error(errors, source, f"query.command must be one of {QUERY_COMMANDS}")
        if not isinstance(query.get("args"), dict):
            _error(errors, source, "query.args must be a mapping")
    if not _nonempty(feedback.get("observation")):
        _error(errors, source, "missing required field: observation")

    source_search = feedback.get("manual_source_search")
    if not isinstance(source_search, dict) or \
            not isinstance(source_search.get("performed"), bool):
        _error(errors, source, "manual_source_search.performed must be a boolean")
    elif source_search["performed"] and not _nonempty(source_search.get("reason")):
        _error(errors, source,
               "manual_source_search.reason is required when performed")

    gap = feedback.get("possible_gap")
    if gap is not None:
        if not isinstance(gap, dict):
            _error(errors, source, "possible_gap must be a mapping or null")
        else:
            if gap.get("category") not in GAP_CATEGORIES:
                _error(errors, source,
                       f"possible_gap.category must be one of {GAP_CATEGORIES}")
            if not _nonempty(gap.get("statement")):
                _error(errors, source, "possible_gap.statement must be non-empty")

    evidence = feedback.get("evidence", [])
    if not isinstance(evidence, list):
        _error(errors, source, "evidence must be a list")
    else:
        for number, item in enumerate(evidence):
            if not isinstance(item, dict) or not _nonempty(item.get("file")):
                _error(errors, source, f"evidence[{number}] must contain a non-empty file")
            elif item.get("lines") is not None and not _lines(item["lines"]):
                _error(errors, source, f"evidence[{number}].lines must be N or N-M")

    sensitivity = feedback.get("sensitivity")
    if not isinstance(sensitivity, dict) or sensitivity.get("contains_sensitive_content") is not False:
        _error(errors, source,
               "sensitivity.contains_sensitive_content must be false; redact before recording")
    return errors
