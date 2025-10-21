"""
log-surgeon: High-performance log parsing and structured data extraction.

This package provides Python FFI bindings to the log-surgeon C++ library,
enabling efficient extraction of structured information from unstructured log files.

Main Classes:
    Parser: High-level parser for extracting structured data from log messages
    Query: Query builder for parsing log events into DataFrames and Arrow Tables
    SchemaCompiler: Compiler for constructing log-surgeon schema definitions
    LogEvent: Represents a parsed log event with extracted variables
    GroupNameResolver: Bidirectional mapping for capture group names

Example:
    >>> from log_surgeon import Parser
    >>> parser = Parser()
    >>> parser.add_var("metric", r"value=(?<value>\\d+)")
    >>> parser.compile()
    >>> event = parser.parse_event("Processing metric value=42")
    >>> print(event['value'])
    42
"""

from .schema_compiler import SchemaCompiler
from .parser import Parser
from .query import Query
from .log_event import LogEvent
from .group_name_resolver import GroupNameResolver
from .pattern import PATTERN

__all__ = [
    "Parser",
    "Query",
    "SchemaCompiler",
    "LogEvent",
    "GroupNameResolver",
    "PATTERN",
]