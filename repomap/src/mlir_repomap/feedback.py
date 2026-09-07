"""CompilerDev compiler-knowledge 使用反馈的校验。

反馈是消费者使用确定性查询的紧凑观察；它不进入 compiler graph、不成为 compiler fact，
也不改变 finding 生命周期。
"""

import re


QUERY_COMMANDS = ("review", "finding-impact", "pipeline-stages", "evidence")
TASK_KINDS = ("compiler-review", "bug-investigation", "pipeline-audit", "other")
GAP_CATEGORIES = ("query-coverage", "evidence-location", "workflow", "documentation",
                  "other")
OBSERVATION_KINDS = ("query-sufficient", "query-insufficient", "adoption-missed",
                     "query-operational")
ORIGINS = ("automatic", "agent", "curated")
CONFIDENCE = ("low", "medium", "high")
CLASSIFICATION_SOURCES = ("heuristic", "human", "policy")
USAGE_COUNTERS = ("compiler_knowledge_calls", "discovery_search_calls",
                  "search_after_query_calls")
USAGE_STEPS = ("first_knowledge_step", "first_discovery_step", "first_edit_step")
OPERATIONAL_BOOLEANS = ("stale_index", "refresh_performed", "not_found", "truncated",
                        "error")
OPERATIONAL_COUNTERS = ("refresh_duration_ms", "diagnostic_count", "duration_ms")


def _error(errors, source, message):
    errors.append(f"{source}: {message}")


def _nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def _lines(value):
    return isinstance(value, int) and value > 0 or (
        isinstance(value, str) and bool(re.fullmatch(r"\d+(-\d+)?", value)))


def _is_counter(value):
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _is_step(value):
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def _unknown_fields(errors, source, value, allowed):
    for key in sorted(set(value) - set(allowed)):
        _error(errors, source, f"unknown field: {key}")


def _validate_task(task, errors, source, strict=False):
    if not isinstance(task, dict):
        _error(errors, source, "task must be a mapping")
        return
    if strict:
        _unknown_fields(errors, source, task, {"kind", "target", "classification"})
    if task.get("kind") not in TASK_KINDS:
        _error(errors, source, f"task.kind must be one of {TASK_KINDS}")
    if not _nonempty(task.get("target")):
        _error(errors, source, "task.target must be a non-empty stable target")
    classification = task.get("classification")
    if classification is not None:
        if not isinstance(classification, dict):
            _error(errors, source, "task.classification must be a mapping")
        else:
            if strict:
                _unknown_fields(errors, source + ".classification", classification,
                                {"confidence", "source"})
            if classification.get("confidence") not in CONFIDENCE:
                _error(errors, source,
                       f"task.classification.confidence must be one of {CONFIDENCE}")
            if classification.get("source") not in CLASSIFICATION_SOURCES:
                _error(errors, source,
                       "task.classification.source must explicitly be heuristic, human, or policy")


def _validate_query(query, errors, source, strict=False):
    if not isinstance(query, dict):
        _error(errors, source, "query must be a mapping")
        return
    if strict:
        _unknown_fields(errors, source, query, {"command", "args"})
    if query.get("command") not in QUERY_COMMANDS:
        _error(errors, source, f"query.command must be one of {QUERY_COMMANDS}")
    if not isinstance(query.get("args"), dict):
        _error(errors, source, "query.args must be a mapping")


def _validate_manual_source_search(value, errors, source, strict=False):
    if not isinstance(value, dict):
        _error(errors, source, "manual_source_search must be a mapping")
        return
    if strict:
        _unknown_fields(errors, source, value, {"performed", "reason"})
    if not isinstance(value.get("performed"), bool):
        _error(errors, source, "manual_source_search.performed must be a boolean")
    elif value["performed"] and not _nonempty(value.get("reason")):
        _error(errors, source, "manual_source_search.reason is required when performed")


def _validate_gap(gap, errors, source, strict=False):
    if gap is None:
        return
    if not isinstance(gap, dict):
        _error(errors, source, "possible_gap must be a mapping or null")
        return
    if strict:
        _unknown_fields(errors, source, gap, {"category", "statement"})
    if gap.get("category") not in GAP_CATEGORIES:
        _error(errors, source, f"possible_gap.category must be one of {GAP_CATEGORIES}")
    if not _nonempty(gap.get("statement")):
        _error(errors, source, "possible_gap.statement must be non-empty")


def _validate_evidence(evidence, errors, source, strict=False):
    if not isinstance(evidence, list):
        _error(errors, source, "evidence must be a list")
        return
    for number, item in enumerate(evidence):
        item_source = f"{source}[{number}]"
        if not isinstance(item, dict) or not _nonempty(item.get("file")):
            _error(errors, source, f"evidence[{number}] must contain a non-empty file")
        else:
            if strict:
                _unknown_fields(errors, item_source, item, {"file", "lines"})
            if item.get("lines") is not None and not _lines(item["lines"]):
                _error(errors, source, f"evidence[{number}].lines must be N or N-M")


def _validate_sensitivity(sensitivity, errors, source, strict=False):
    if not isinstance(sensitivity, dict) or \
            sensitivity.get("contains_sensitive_content") is not False:
        _error(errors, source,
               "sensitivity.contains_sensitive_content must be false; redact before recording")
    elif strict:
        _unknown_fields(errors, source, sensitivity, {"contains_sensitive_content"})


def _validate_v1(feedback, errors, source):
    """为已有工件兼容保留 v1 宽松的嵌套字段行为。"""
    _validate_task(feedback.get("task"), errors, source + ".task")
    _validate_query(feedback.get("query"), errors, source + ".query")
    if not _nonempty(feedback.get("observation")):
        _error(errors, source, "missing required field: observation")
    _validate_manual_source_search(feedback.get("manual_source_search"), errors,
                                   source + ".manual_source_search")
    _validate_gap(feedback.get("possible_gap"), errors, source + ".possible_gap")
    _validate_evidence(feedback.get("evidence", []), errors, source + ".evidence")
    _validate_sensitivity(feedback.get("sensitivity"), errors, source + ".sensitivity")


def _validate_route(route, errors, source):
    if not isinstance(route, dict):
        _error(errors, source, "route must be a mapping")
        return
    _unknown_fields(errors, source, route, {"knowledge_expected", "kind", "confidence"})
    if not isinstance(route.get("knowledge_expected"), bool):
        _error(errors, source, "route.knowledge_expected must be a boolean")
    if not _nonempty(route.get("kind")):
        _error(errors, source, "route.kind must be a non-empty routing kind")
    if route.get("confidence") not in CONFIDENCE:
        _error(errors, source, f"route.confidence must be one of {CONFIDENCE}")


def _validate_usage(usage, errors, source):
    if not isinstance(usage, dict):
        _error(errors, source, "usage must be a mapping")
        return
    _unknown_fields(errors, source, usage,
                    set(USAGE_COUNTERS + USAGE_STEPS + ("knowledge_commands",)))
    for field in USAGE_COUNTERS:
        if field in usage and not _is_counter(usage[field]):
            _error(errors, source, f"usage.{field} must be a non-negative integer")
    for field in USAGE_STEPS:
        if field in usage and not _is_step(usage[field]):
            _error(errors, source, f"usage.{field} must be a positive integer step")
    commands = usage.get("knowledge_commands")
    if commands is not None:
        if not isinstance(commands, dict):
            _error(errors, source, "usage.knowledge_commands must be a mapping")
        else:
            for command, count in commands.items():
                if command not in QUERY_COMMANDS or not _is_counter(count):
                    _error(errors, source,
                           "usage.knowledge_commands must map adapter commands to non-negative integers")
                    break


def _validate_operational(operational, errors, source):
    if operational is None:
        return
    if not isinstance(operational, dict):
        _error(errors, source, "operational must be a mapping")
        return
    _unknown_fields(errors, source, operational,
                    set(OPERATIONAL_BOOLEANS + OPERATIONAL_COUNTERS))
    for field in OPERATIONAL_BOOLEANS:
        if field in operational and not isinstance(operational[field], bool):
            _error(errors, source, f"operational.{field} must be a boolean")
    for field in OPERATIONAL_COUNTERS:
        if field in operational and not _is_counter(operational[field]):
            _error(errors, source, f"operational.{field} must be a non-negative integer")


def _validate_v2(feedback, errors, source):
    allowed = {"schema_version", "created_at", "origin", "observation_kind", "task", "query",
               "route", "usage", "operational", "observation", "manual_source_search",
               "possible_gap", "evidence", "sensitivity"}
    _unknown_fields(errors, source, feedback, allowed)
    for field in ("created_at", "origin", "observation_kind", "task", "route", "usage",
                  "observation", "manual_source_search", "sensitivity"):
        if field not in feedback:
            _error(errors, source, f"missing required field: {field}")
    if feedback.get("origin") not in ORIGINS:
        _error(errors, source, f"origin must be one of {ORIGINS}")
    kind = feedback.get("observation_kind")
    if kind not in OBSERVATION_KINDS:
        _error(errors, source, f"observation_kind must be one of {OBSERVATION_KINDS}")
    _validate_task(feedback.get("task"), errors, source + ".task", strict=True)
    _validate_route(feedback.get("route"), errors, source + ".route")
    _validate_usage(feedback.get("usage"), errors, source + ".usage")
    _validate_operational(feedback.get("operational"), errors, source + ".operational")
    if not _nonempty(feedback.get("observation")):
        _error(errors, source, "missing required field: observation")
    _validate_manual_source_search(feedback.get("manual_source_search"), errors,
                                   source + ".manual_source_search", strict=True)
    _validate_gap(feedback.get("possible_gap"), errors, source + ".possible_gap", strict=True)
    _validate_evidence(feedback.get("evidence", []), errors, source + ".evidence", strict=True)
    _validate_sensitivity(feedback.get("sensitivity"), errors, source + ".sensitivity",
                          strict=True)

    query = feedback.get("query")
    if kind == "adoption-missed":
        if query is not None:
            _error(errors, source, "adoption-missed requires query: null")
        route = feedback.get("route")
        if isinstance(route, dict) and route.get("knowledge_expected") is not True:
            _error(errors, source,
                   "adoption-missed requires route.knowledge_expected=true")
        usage = feedback.get("usage")
        if not isinstance(usage, dict) or usage.get("compiler_knowledge_calls") != 0:
            _error(errors, source,
                   "adoption-missed requires usage.compiler_knowledge_calls=0")
    else:
        if "query" not in feedback or query is None:
            _error(errors, source, f"{kind or 'v2 observation'} requires query")
        else:
            _validate_query(query, errors, source + ".query", strict=True)


def validate_feedback(data, source="<feedback>"):
    """校验一个 feedback 工件；返回空列表表示有效。

    校验器仅使用标准库且不持久化：它不能调用 Agent、打开索引、创建 graph 数据或改变
    finding 生命周期。
    """
    errors = []
    if not isinstance(data, dict) or set(data) != {"feedback"}:
        _error(errors, source, "document must be a single top-level 'feedback' mapping")
        return errors
    feedback = data["feedback"]
    if not isinstance(feedback, dict):
        _error(errors, source, "'feedback' must be a mapping")
        return errors
    version = feedback.get("schema_version")
    if version not in (1, 2):
        _error(errors, source, "schema_version must be 1 or 2")
        return errors
    if not _nonempty(feedback.get("created_at")):
        _error(errors, source, "missing required field: created_at")
    if version == 1:
        _validate_v1(feedback, errors, source)
    else:
        _validate_v2(feedback, errors, source)
    return errors
