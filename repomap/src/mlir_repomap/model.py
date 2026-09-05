"""Entity/edge/evidence model and schema constants for the MLIR RepoMap engine."""

SCHEMA_VERSION = 1
INDEXER_VERSION = 18

CONFIRMED = "confirmed"
INFERRED = "inferred"
HEURISTIC = "heuristic"

# Entity kinds
DIALECT = "dialect"
OP = "op"
TYPE = "type"
ATTR = "attr"
INTERFACE = "interface"
FUNCTION = "function"
ATTRIBUTE = "attribute"
PASS = "pass"
PASS_CLASS = "pass_class"
FACTORY = "factory"
PIPELINE = "pipeline"
PATTERN = "pattern"
TEST = "test"
SYMBOL = "symbol"
FILE = "file"

# Edge kinds
DEFINES = "DEFINES"
DIALECT_OWNS = "DIALECT_OWNS"
PASS_HAS_FACTORY = "PASS_HAS_FACTORY"
PASS_IMPLEMENTS = "PASS_IMPLEMENTS"
PIPELINE_CONTAINS = "PIPELINE_CONTAINS"
PIPELINE_NESTS = "PIPELINE_NESTS"
PIPELINE_CALLS = "PIPELINE_CALLS"
PRECEDES = "PRECEDES"
PASS_USES_PATTERN = "PASS_USES_PATTERN"
PASS_USES_PATTERN_POPULATOR = "PASS_USES_PATTERN_POPULATOR"
FUNCTION_DEFINES_PATTERN = "FUNCTION_DEFINES_PATTERN"
FUNCTION_CALLS = "FUNCTION_CALLS"
PIPELINE_BUILT_BY = "PIPELINE_BUILT_BY"
PATTERN_MATCHES_OP = "PATTERN_MATCHES_OP"
PATTERN_CREATES_OP = "PATTERN_CREATES_OP"
CREATES_ATTRIBUTE = "CREATES_ATTRIBUTE"
TEST_COVERS_PASS = "TEST_COVERS_PASS"
TEST_EXERCISES_PIPELINE = "TEST_EXERCISES_PIPELINE"
REFERENCES = "REFERENCES"


class Evidence:
    __slots__ = ("file", "line_start", "line_end", "snippet", "extractor", "confidence")

    def __init__(self, file, line_start, line_end=None, snippet="", extractor="",
                 confidence=CONFIRMED):
        self.file = file
        self.line_start = line_start
        self.line_end = line_end or line_start
        self.snippet = (snippet or "").strip()[:200]
        self.extractor = extractor
        self.confidence = confidence

    def to_dict(self):
        return {"file": self.file, "line_start": self.line_start,
                "line_end": self.line_end, "snippet": self.snippet,
                "extractor": self.extractor, "confidence": self.confidence}


class Node:
    __slots__ = ("id", "kind", "name", "summary", "file", "line")

    def __init__(self, id, kind, name, summary="", file="", line=None):
        self.id = id
        self.kind = kind
        self.name = name
        self.summary = (summary or "").strip()[:300]
        self.file = file
        self.line = line

    def to_dict(self):
        return {"id": self.id, "kind": self.kind, "name": self.name,
                "summary": self.summary, "file": self.file, "line": self.line}


class Edge:
    __slots__ = ("src", "dst", "kind", "props", "evidence")

    def __init__(self, src, dst, kind, props=None, evidence=None):
        self.src = src
        self.dst = dst
        self.kind = kind
        self.props = props or {}
        self.evidence = evidence  # single Evidence for MVP; store dedups by key

    def key(self):
        """Identity of the relation (evidences attach to this key)."""
        p = "|".join(f"{k}={self.props[k]}" for k in sorted(self.props))
        return f"{self.src}\t{self.dst}\t{self.kind}\t{p}"


DIAG_SCHEMA = """CREATE TABLE IF NOT EXISTS diagnostics (
    file TEXT PRIMARY KEY, message TEXT)"""
