r"""
log-surgeon: High-performance log parsing and structured data extraction.

This package provides Python FFI bindings to the log-surgeon C++ library,
enabling efficient extraction of structured information from unstructured log files.

Main Classes:
    Parser: High-level parser for extracting structured data from log messages
    JsonParser: Parser for JSON-formatted logs with field-specific extraction
    Query: Query builder for parsing log events into DataFrames and Arrow Tables
    SchemaCompiler: Compiler for constructing log-surgeon schema definitions
    LogEvent: Represents a parsed log event with extracted variables
    ConflictStrategy: Enum for JsonParser conflict resolution strategies

Example:
    >>> from log_surgeon import Parser
    >>> parser = Parser()
    >>> parser.add_var("metric", r"value=(?<value>\\d+)")
    >>> parser.compile()
    >>> event = parser.parse_event("Processing metric value=42")
    >>> print(event["value"])
    42

Example with JSON logs:
    >>> from log_surgeon import JsonParser, Parser
    >>> parser = Parser()
    >>> parser.add_var("user_info", r"user=(?<user_id>\\d+)")
    >>> parser.compile()
    >>> json_parser = JsonParser(parser).parse_fields(["message"])
    >>> result = json_parser.parse_one('{"message": "user=123"}')
    >>> print(result["extracted"]["user_id"])
    123

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
