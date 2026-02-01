r"""
log-surgeon: High-performance log parsing and structured data extraction.

This package provides Python FFI bindings to the log-surgeon C++ library,
enabling efficient extraction of structured information from unstructured log files.
The library uses DFA (Deterministic Finite Automaton) compilation for high-performance
single-pass parsing.

Key Concepts
------------
**Delimiter-Based Matching**
    Unlike standard regex where `.` matches any character except newline, in log-surgeon
    `.` matches any character **except delimiters** (spaces, tabs, colons, etc.). This
    enables efficient tokenization but requires explicit character classes to match
    across delimiters.

**Named Capture Groups**
    Use `(?<name>pattern)` syntax to extract specific values from log messages.
    Captured values are accessible via dictionary-style access on LogEvent objects.

**Variable Priority**
    When multiple patterns could match, higher-priority variables are tried first.
    Use the `priority` parameter in `add_var()` to control matching order.

Main Classes
------------
Parser
    High-level parser for extracting structured data from text log messages.
    Provides a fluent API for defining patterns and parsing logs.

JsonParser
    Specialized parser for JSON-formatted logs. Wraps a Parser instance and
    applies extraction rules to JSON string fields, then merges results back
    into the original JSON structure.

Query
    Query builder for parsing log events into pandas DataFrames or PyArrow Tables.
    Supports field selection, filtering, and log type analysis.

LogEvent
    Represents a parsed log event with extracted variables and metadata.
    Provides dictionary-style access to captured values.

SchemaCompiler
    Low-level compiler for constructing log-surgeon schema definitions.
    Used internally by Parser but can be used directly for advanced use cases.

PATTERN
    Collection of pre-built regex patterns for common log elements like
    IP addresses, UUIDs, integers, file paths, and Java stack traces.

ConflictStrategy
    Enum defining how JsonParser handles conflicts when extracted variable
    names match existing JSON keys (NEST, PREFIX, OVERWRITE, RAISE).

Basic Usage
-----------
```python
from log_surgeon import Parser, PATTERN

# Create and configure parser
parser = Parser()
parser.add_var("metric", rf"value=(?<value>{PATTERN.INT})")
parser.compile()

# Parse a single event
event = parser.parse_event("Processing value=42")
print(event["value"])  # "42"
print(event.get_log_type())  # "Processing value=<value>"

# Parse multiple events from a file
with open("app.log") as f:
    for event in parser.parse(f):
        print(event["value"])
```

JSON Log Parsing
----------------
```python
from log_surgeon import JsonParser, Parser

# Create underlying parser with extraction patterns
parser = Parser()
parser.add_var("user_info", r"user=(?<user_id>\d+)")
parser.compile()

# Create JSON parser targeting the "message" field
json_parser = JsonParser(parser).target_fields(["message"])

# Parse JSON log
result = json_parser.parse_one('{"ts": "2024-01-01", "message": "user=123"}')
print(result["extracted"]["user_id"])  # "123"
```

Exporting to DataFrame
----------------------
```python
from log_surgeon import Parser, Query

parser = Parser()
parser.add_var("metric", r"value=(?<value>\d+)")
parser.compile()

# Export parsed events to pandas DataFrame
df = Query(parser).select(["value"]).from_(log_data).to_dataframe()
```

See Also
--------
- GitHub: https://github.com/y-scope/log-surgeon-ffi-py
- Documentation: https://y-scope.github.io/log-surgeon-ffi-py

"""

from .json_parser import ConflictStrategy, JsonParser
from .log_event import LogEvent
from .parser import Parser
from .pattern import PATTERN
from .query import Query
from .schema_compiler import SchemaCompiler

__all__ = [
    "PATTERN",
    "ConflictStrategy",
    "JsonParser",
    "LogEvent",
    "Parser",
    "Query",
    "SchemaCompiler",
]
