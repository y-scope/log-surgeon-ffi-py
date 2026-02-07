"""
High-level parser for extracting structured data from unstructured log messages.

This module provides the Parser class, which is the main entry point for parsing
text-based log files. It supports pattern definition, schema compilation, and
efficient streaming parsing of log data.

The parser uses log-surgeon's DFA-based matching engine for high-performance
single-pass parsing of log messages.

Example
-------
```python
from log_surgeon import Parser, PATTERN

parser = Parser()
parser.add_var("request", rf"GET (?<path>/[^ ]+) (?<status>{PATTERN.INT})")
parser.compile()

for event in parser.parse(log_file):
    print(f"{event['path']} -> {event['status']}")
```

See Also
--------
JsonParser : For parsing JSON-formatted logs.
Query : For exporting parsed events to DataFrames.
"""

from __future__ import annotations

import io
import os
from typing import BinaryIO, TextIO, TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Generator

    from log_surgeon._rust_backend import RustBackend
    from log_surgeon.log_event import LogEvent

from log_surgeon.schema_compiler import SchemaCompiler

try:
    from log_surgeon_ffi import ReaderParser  # type: ignore[attr-defined]
except ImportError:
    ReaderParser = None  # type: ignore[assignment, misc]

_PARSER_NOT_INITIALIZED_ERROR = (
    "Parser not initialized. Load a log surgeon schema using load_schema() or compile()"
)


class Parser:
    r"""
    High-level parser for extracting structured data from unstructured log messages.

    The Parser uses a schema-based approach to identify patterns, extract variables,
    and generate log types from raw log text. It compiles patterns into a DFA
    (Deterministic Finite Automaton) for efficient single-pass matching.

    Key Features
    ------------
    - **Named capture groups**: Use `(?<name>pattern)` to extract specific values
    - **Priority-based matching**: Control which patterns are tried first
    - **Log type generation**: Automatically creates templates from matched patterns
    - **Streaming parsing**: Efficiently process large log files
    - **Multiple input sources**: Parse from strings, files, or streams

    Delimiter-Based Matching
    ------------------------
    Unlike standard regex, log-surgeon uses delimiter-based matching where `.`
    matches any character **except delimiters** (spaces, tabs, colons, etc.).
    This is important for pattern design:

    ```python
    # With default delimiters, "." stops at spaces
    parser.add_var("token", r"(?<match>d.*)")
    event = parser.parse_event("abc def ghi")
    print(event['match'])  # "def" (NOT "def ghi")

    # To match across spaces, use explicit character classes
    parser.add_var("multi", r"(?<match>d[a-z ]*i)")  # Includes space
    ```

    Workflow
    --------
    1. Create a Parser instance with optional custom delimiters
    2. Add variable patterns using `add_var()`
    3. Call `compile()` to build the DFA
    4. Parse logs using `parse()` or `parse_event()`

    Example
    -------
    ```python
    from log_surgeon import Parser, PATTERN

    parser = Parser()
    parser.add_var("request", rf"(?<method>GET|POST) (?<path>/[^ ]+)")
    parser.add_var("status", rf"status=(?<code>{PATTERN.INT})")
    parser.compile()

    event = parser.parse_event("GET /api/users status=200")
    print(event["method"])  # "GET"
    print(event["path"])    # "/api/users"
    print(event["code"])    # "200"
    print(event.get_log_type())  # "<method> <path> status=<code>"
    ```

    See Also
    --------
    JsonParser : For parsing JSON-formatted logs.
    Query : For exporting parsed events to DataFrames.
    PATTERN : Pre-built regex patterns for common log elements.
    """

    def __init__(
        self, delimiters: str = r" \t\r\n:,!;%@/()[]", backend: str | None = None
    ) -> None:
        r"""
        Initialize the parser with optional custom delimiters.

        Delimiters define token boundaries for log-surgeon's matching engine.
        The `.` metacharacter in patterns will NOT match delimiter characters,
        which affects how patterns are written.

        Args:
            delimiters: String of delimiter characters for tokenization.
                Default: `" \t\r\n:,!;%@/()[]"` (space, tab, newline, and common punctuation).

                Common customizations:

                - Remove `:` to match timestamps like "10:30:00" as single tokens
                - Remove `/` to match file paths as single tokens
                - Add `=` to treat key=value pairs as separate tokens

            backend: Backend engine to use for parsing. Either "cpp" (uses the
                C++ log-surgeon library) or "rust" (uses the Rust log-mechanic
                library via cffi). If not specified, reads from the
                ``LOG_SURGEON_BACKEND`` environment variable, defaulting to
                "cpp".

        Note
        ----
        Delimiter choice significantly affects pattern matching. For example,
        with default delimiters, a pattern like `(?<ip>.*)` will stop at the
        first space. To match an IP address, use explicit character classes:
        `(?<ip>[0-9.]+)` or the pre-built `PATTERN.IPV4`.

        Example
        -------
        ```python
        # Default delimiters
        parser = Parser()

        # Custom delimiters for file path matching
        parser = Parser(delimiters=r" \t\r\n:,!;%@()[]")  # Removed "/"

        # Minimal delimiters for maximum token length
        parser = Parser(delimiters=r" \t\r\n")

        # Use Rust backend
        parser = Parser(backend="rust")
        ```

        """
        if backend is None:
            backend = os.environ.get("LOG_SURGEON_BACKEND", "cpp")
        if backend not in ("cpp", "rust"):
            msg = f"backend must be 'cpp' or 'rust', got '{backend}'"
            raise ValueError(msg)
        self._backend = backend
        self._parser: ReaderParser | None = None  # type: ignore[annotation-unchecked]
        self._rust_backend: RustBackend | None = None
        self._schema_compiler: SchemaCompiler = SchemaCompiler(delimiters)
        self._enable_debug = False

    def add_var(self, name: str, regex: str, priority: int = 0) -> Parser:
        r"""
        Add a variable pattern to the parser's schema.

        Patterns must include at least one named capture group using `(?<name>...)`
        syntax. The captured values are accessible on parsed LogEvent objects using
        dictionary-style access: `event["name"]`.

        Args:
            name: Unique identifier for this variable pattern. Used for schema
                organization but not directly accessible on LogEvent (use capture
                group names instead).
            regex: Regular expression pattern with named capture groups.
                Use `(?<name>pattern)` syntax to define extractable fields.
                The `.` metacharacter matches any character except delimiters.
            priority: Controls pattern matching order (higher = tried first).
                Default is 0.

                - Use positive values for specific patterns (e.g., IP addresses)
                - Use negative values for generic patterns (e.g., catch-all integers)
                - Variables with equal priority maintain insertion order

        Returns:
            Self for method chaining.

        Raises:
            ValueError: If the pattern has no named capture groups, or if capture
                group names contain delimiter characters.
            AttributeError: If a variable with the same name already exists.

        Note
        ----
        **Priority Example**: If you have patterns for IP addresses and integers,
        give IP higher priority so "192.168.1.1" matches as an IP, not four integers.

        Example
        -------
        ```python
        from log_surgeon import Parser, PATTERN

        parser = Parser()

        # High priority for specific patterns
        parser.add_var("ip_address", rf"(?<ip>{PATTERN.IPV4})", priority=10)

        # Default priority for normal patterns
        parser.add_var("request", r"(?<method>GET|POST) (?<path>/\S+)")

        # Low priority for generic catch-all patterns
        parser.add_var("number", rf"(?<num>{PATTERN.INT})", priority=-1)

        parser.compile()
        ```

        """
        self._schema_compiler.add_var(name, regex, priority)
        return self

    def add_timestamp(self, name: str, regex: str) -> Parser:
        r"""
        Add a timestamp pattern to the parser's schema.

        Timestamps are special patterns that log-surgeon uses for log event
        boundary detection. When a timestamp pattern matches at the start of
        a line, it signals the beginning of a new log event.

        Args:
            name: Unique identifier for this timestamp pattern. Multiple timestamp
                patterns can be added for logs with varying timestamp formats.
            regex: Regular expression pattern for matching timestamps.
                Should match the complete timestamp format used in your logs.

        Returns:
            Self for method chaining.

        Note
        ----
        Timestamp patterns help log-surgeon correctly handle multi-line log events
        (e.g., stack traces). Without timestamps, each line is treated as a separate
        event.

        Example
        -------
        ```python
        parser = Parser()

        # ISO 8601 format: 2024-01-15T10:30:00
        parser.add_timestamp("iso8601", r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")

        # Common log format: 15/Jan/2024:10:30:00
        parser.add_timestamp("clf", r"\d{2}/[a-zA-Z]{3}/\d{4}:\d{2}:\d{2}:\d{2}")

        # Unix timestamp: 1705312200
        parser.add_timestamp("unix", r"\d{10}")

        parser.compile()
        ```

        """
        self._schema_compiler.add_timestamp(name, regex)
        return self

    def compile(self, enable_debug_logs: bool = False) -> None:
        r"""
        Compile the schema and initialize the parser for use.

        This method builds a DFA (Deterministic Finite Automaton) from the
        configured patterns and prepares the parser for log processing.
        Must be called after adding all variables and timestamps, and before
        any parsing operations.

        Args:
            enable_debug_logs: If True, output debug information to stderr during
                compilation and parsing. Useful for troubleshooting pattern issues.
                Default is False.

        Raises:
            RuntimeError: If schema compilation fails due to invalid patterns
                or conflicting configurations.

        Warning
        -------
        After calling `compile()`, the parser's schema is fixed. Adding new
        variables or timestamps will not affect the compiled parser. Create
        a new Parser instance if you need different patterns.

        Example
        -------
        ```python
        parser = Parser()
        parser.add_var("metric", r"value=(?<value>\d+)")
        parser.add_var("status", r"status=(?<status>[a-zA-Z0-9_]+)")

        # Compile once all patterns are defined
        parser.compile()

        # Now ready for parsing
        for event in parser.parse(log_file):
            print(event["value"])
        ```

        """
        if self._backend == "rust":
            from log_surgeon._rust_backend import RustBackend  # noqa: PLC0415

            self._rust_backend = RustBackend(self._schema_compiler, enable_debug_logs)
        else:
            if ReaderParser is None:
                msg = (
                    "C++ backend (log_surgeon_ffi) is not installed. "
                    "Install with: pip install log-surgeon-ffi, "
                    "or use backend='rust'."
                )
                raise ImportError(msg)
            self._parser = ReaderParser(
                io.BytesIO(),
                self._schema_compiler.compile(),
                enable_debug_logs,
            )

    def parse_event(self, payload: str) -> LogEvent | None:
        r"""
        Parse a single log event from a string.

        Convenience method for parsing a single log message. For multiple
        events or streaming parsing, use `parse()` instead.

        Args:
            payload: Log message string to parse. Can be a single line or
                multi-line string (e.g., containing a stack trace).

        Returns:
            LogEvent containing extracted variables and metadata, or None
            if no patterns matched.

        Raises:
            RuntimeError: If `compile()` has not been called.

        Note
        ----
        This method creates a new stream for each call, which has overhead.
        For batch processing, use `parse()` with all log data at once.

        Example
        -------
        ```python
        parser = Parser()
        parser.add_var("metric", r"value=(?<value>\d+)")
        parser.compile()

        event = parser.parse_event("Processing value=42")
        if event:
            print(event["value"])        # "42"
            print(event.get_log_type())  # "Processing value=<value>"
        ```

        """
        for event in self.parse(payload):
            return event
        return None

    def parse(
        self, source: str | TextIO | BinaryIO | io.StringIO | io.BytesIO
    ) -> Generator[LogEvent, None, None]:
        r"""
        Parse log events from an input source.

        Generator that yields LogEvent objects for each parsed event. Supports
        multiple input types for flexibility in how log data is provided.

        Args:
            source: Input data to parse. Accepts:

                - `str`: String containing log data (one or more lines)
                - `TextIO`: File opened in text mode (`open("file.log", "r")`)
                - `BinaryIO`: File opened in binary mode (`open("file.log", "rb")`)
                - `io.StringIO`: In-memory text stream
                - `io.BytesIO`: In-memory binary stream

        Yields:
            LogEvent: Parsed event with extracted variables accessible via
            dictionary-style access (e.g., `event["field_name"]`).

        Raises:
            RuntimeError: If `compile()` has not been called.
            TypeError: If source type is not supported.

        Note
        ----
        For file objects, the entire content is read into memory before parsing.
        For very large files, consider reading and parsing in chunks.

        Example
        -------
        ```python
        parser = Parser()
        parser.add_var("request", r"(?<method>GET|POST) (?<path>/\S+)")
        parser.compile()

        # Parse from multi-line string
        logs = '''GET /api/users
        POST /api/login
        GET /api/status'''

        for event in parser.parse(logs):
            print(f"{event['method']} {event['path']}")

        # Parse from file
        with open("access.log") as f:
            for event in parser.parse(f):
                print(event['path'])

        # Parse from BytesIO (e.g., from network response)
        import io
        data = io.BytesIO(b"GET /health\nGET /ready")
        for event in parser.parse(data):
            print(event['path'])
        ```

        """
        self._ensure_initialized()

        if self._backend == "rust":
            text = self._read_source_as_string(source)
            assert self._rust_backend is not None
            yield from self._rust_backend.parse(text)
        else:
            # C++ backend path
            input_stream: io.StringIO | io.BytesIO
            if isinstance(source, str):
                input_stream = io.StringIO(source)
            elif isinstance(source, (io.StringIO, io.BytesIO)):
                input_stream = source
            elif hasattr(source, "read"):
                content = source.read()
                if isinstance(content, bytes):
                    input_stream = io.BytesIO(content)
                elif isinstance(content, str):
                    input_stream = io.StringIO(content)
                else:
                    msg = f"File object returned unsupported type {type(content).__name__}"
                    raise TypeError(msg)
            else:
                msg = (
                    f"Input must be str, file object, io.StringIO, or io.BytesIO, "
                    f"got {type(source).__name__}"
                )
                raise TypeError(msg)

            assert self._parser is not None
            self._parser.reset_input_stream(input_stream)
            while (event := self._parser.parse_next_log_event()) is not None:
                yield event

    def get_vars(self) -> set[str]:
        r"""
        Get all capture group names defined in the schema.

        Returns the names of all capture groups from patterns added via `add_var()`.
        These names correspond to the keys available on parsed LogEvent objects.

        Returns:
            Set of capture group names that can be used to access extracted
            values from LogEvent objects.

        Note
        ----
        This returns capture group names, not variable names. A single `add_var()`
        call can define multiple capture groups.

        Example
        -------
        ```python
        parser = Parser()
        # This adds two capture groups: "method" and "path"
        parser.add_var("request", r"(?<method>GET|POST) (?<path>/\S+)")
        # This adds one capture group: "code"
        parser.add_var("status", r"status=(?<code>\d+)")
        parser.compile()

        print(parser.get_vars())  # {'method', 'path', 'code'}
        ```

        """
        return self._schema_compiler.get_all_capture_group_names()

    @staticmethod
    def _read_source_as_string(source: str | TextIO | BinaryIO | io.StringIO | io.BytesIO) -> str:
        """Convert any supported source type to a string."""
        if isinstance(source, str):
            return source
        if isinstance(source, io.StringIO):
            return source.read()
        if isinstance(source, io.BytesIO):
            return source.read().decode("utf-8")
        if hasattr(source, "read"):
            content = source.read()
            if isinstance(content, bytes):
                return content.decode("utf-8")
            if isinstance(content, str):
                return content
            msg = f"File object returned unsupported type {type(content).__name__}"
            raise TypeError(msg)
        msg = (
            f"Input must be str, file object, io.StringIO, or io.BytesIO, "
            f"got {type(source).__name__}"
        )
        raise TypeError(msg)

    def _ensure_initialized(self) -> None:
        """
        Ensure the parser has been initialized with a schema.

        Raises:
            RuntimeError: If parser is not initialized

        """
        if self._parser is None and self._rust_backend is None:
            raise RuntimeError(_PARSER_NOT_INITIALIZED_ERROR)
