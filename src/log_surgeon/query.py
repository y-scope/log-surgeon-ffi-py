r"""
Query builder for extracting and exporting structured log data.

This module provides the Query class, which offers a fluent interface for
transforming parsed log events into structured data formats suitable for
analysis and data science workflows.

Key Capabilities
----------------
- **Field selection**: Choose which extracted variables to include
- **Filtering**: Apply predicates to select specific events
- **DataFrame export**: Convert to pandas DataFrames for analysis
- **Arrow export**: Convert to PyArrow Tables for efficient storage
- **Log type analysis**: Analyze patterns and their frequencies

The Query class works with both Parser (for text logs) and JsonParser
(for JSON logs), providing a unified interface for data export.

Example
-------
```python
from log_surgeon import Parser, Query

parser = Parser()
parser.add_var("request", r"(?<method>GET|POST) (?<path>/\S+) (?<code>\d+)")
parser.compile()

# Export to DataFrame with filtering
df = (
    Query(parser)
    .select(["method", "path", "code"])
    .filter(lambda e: e["code"] != "200")
    .from_(log_file)
    .to_dataframe()
)

print(df.head())
#   method          path code
# 0   POST       /login  401
# 1    GET  /api/secret  403
```

See Also
--------
Parser : For parsing text log files.
JsonParser : For parsing JSON log files.
"""

from __future__ import annotations

import io
import json
from typing import Any, BinaryIO, Callable, TextIO, TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Generator

    import pandas as pd  # type: ignore[import-untyped]
    import pyarrow as pa  # type: ignore[import-untyped]

    from log_surgeon.log_event import LogEvent

from log_surgeon.json_parser import JsonParser
from log_surgeon.parser import Parser

try:
    import pandas as pd
except ImportError:
    pd = None

try:
    import pyarrow as pa
except ImportError:
    pa = None

_DATAFRAME_IMPORT_ERROR = (
    "pandas is required for this operation. "
    "Install it with: pip install 'log-surgeon-ffi[dataframe]' or pip install pandas"
)

_ARROW_IMPORT_ERROR = (
    "pyarrow is required for this operation. "
    "Install it with: pip install 'log-surgeon-ffi[arrow]' or pip install pyarrow"
)


class Query:
    r"""
    Query builder for parsing log events into structured data formats.

    Query provides a fluent interface for extracting, filtering, and exporting
    log data to pandas DataFrames or PyArrow Tables. It works with both Parser
    (for text logs) and JsonParser (for JSON logs).

    Workflow
    --------
    1. Create a Query with a compiled Parser or JsonParser
    2. Select fields to extract using `select()`
    3. Optionally filter events using `filter()`
    4. Set the input source using `from_()`
    5. Export using `to_dataframe()` or `to_arrow()`

    Key Features
    ------------
    - **Field selection**: Choose specific fields or use `"*"` for all
    - **Filtering**: Apply lambda predicates to select events
    - **Multiple exports**: DataFrame, Arrow Table, or raw rows
    - **Log type analysis**: Get unique log types and their counts

    Special Fields
    --------------
    In addition to capture group names, you can select:

    - `"@log_type"`: The log type template
    - `"@log_message"`: The original log message
    - `"*"`: All capture groups (Parser only)

    Example
    -------
    ```python
    from log_surgeon import Parser, Query, PATTERN

    parser = Parser()
    parser.add_var("request", rf"(?<method>GET|POST) (?<path>/\S+)")
    parser.add_var("status", rf"(?<code>{PATTERN.INT})")
    parser.compile()

    # Basic query
    df = (
        Query(parser)
        .select(["method", "path", "code"])
        .from_(log_file)
        .to_dataframe()
    )

    # With filtering
    errors_df = (
        Query(parser)
        .select(["@log_message", "code"])
        .filter(lambda e: int(e["code"]) >= 400)
        .from_(log_file)
        .to_dataframe()
    )

    # Log type analysis
    query = Query(parser).from_(log_file)
    for log_type, count in query.get_log_type_counts().items():
        print(f"{count:5d} {log_type}")
    ```

    JsonParser Example
    ------------------
    ```python
    json_parser = JsonParser(parser).target_fields(["message"])

    df = (
        Query(json_parser)
        .select(["extracted.user_id", "extracted.action"])
        .from_(ndjson_file)
        .to_dataframe()
    )
    ```

    See Also
    --------
    Parser : For creating text log parsers.
    JsonParser : For creating JSON log parsers.
    """

    def __init__(self, parser: Parser | JsonParser) -> None:
        r"""
        Initialize a query builder with a parser.

        Creates a new Query instance that will use the given parser to
        process log data. The parser must be compiled before use.

        Args:
            parser: A compiled Parser or JsonParser instance. The parser's
                patterns determine what fields can be selected and filtered.

        Example
        -------
        ```python
        # With Parser (text logs)
        parser = Parser()
        parser.add_var("metric", r"value=(?<value>\d+)")
        parser.compile()
        query = Query(parser)

        # With JsonParser (JSON logs)
        json_parser = JsonParser(parser).target_fields(["message"])
        query = Query(json_parser)
        ```

        """
        self.fields: list[str] | None = None
        self.stream: io.StringIO | io.BytesIO | None = None
        self.parser: Parser | JsonParser = parser
        self.predicate: Callable[[LogEvent], bool] | Callable[[dict[str, Any]], bool] | None = None
        self._is_json_parser: bool = isinstance(parser, JsonParser)

    def filter(
        self, predicate: Callable[[LogEvent], bool] | Callable[[dict[str, Any]], bool]
    ) -> Query:
        """
        Filter log events using a predicate function.

        Applies a filter to include only events where the predicate returns True.
        Events where the predicate returns False are excluded from the output.

        Args:
            predicate: Function that receives an event and returns a boolean.

                - For Parser: receives a `LogEvent` object
                - For JsonParser: receives a `dict` (the enriched JSON)

                Return `True` to include the event, `False` to exclude it.

        Returns:
            Self for method chaining.

        Warning
        -------
        Only one filter can be active. Calling `filter()` multiple times
        replaces the previous predicate. Combine conditions in a single
        predicate using `and`/`or` operators.

        Note
        ----
        Handle missing fields gracefully with try/except or `.get()` to avoid
        errors when a capture group does not match in some events.

        Example
        -------
        ```python
        # Simple value filter
        query.filter(lambda e: int(e["status_code"]) >= 400)

        # Multiple conditions
        query.filter(lambda e: e["method"] == "POST" and int(e["code"]) != 200)

        # Safe filter for optional fields
        def is_error(event):
            try:
                return int(event["code"]) >= 500
            except (KeyError, ValueError):
                return False
        query.filter(is_error)

        # JsonParser filter (receives dict)
        query.filter(lambda obj: obj.get("level") == "ERROR")

        # Access nested JsonParser fields
        query.filter(lambda obj: obj.get("extracted", {}).get("user_id") == "admin")
        ```

        """
        self.predicate = predicate
        return self

    def select(self, fields: list[str]) -> Query:
        """
        Select fields to include in the output.

        Specifies which extracted variables and metadata to include when
        exporting to DataFrame or Arrow Table. Fields appear as columns
        in the order specified.

        Args:
            fields: List of field names to extract. Supports:

                **Capture groups** (from your patterns):
                    `["user_id", "path", "status_code"]`

                **Wildcard** (Parser only):
                    `["*"]` - Selects all capture groups

                **Metadata fields**:
                    - `"@log_type"` - The log type template
                    - `"@log_message"` - The original log message

                **JsonParser fields**:
                    Dot-notation for nested access: `["extracted.user_id"]`

        Returns:
            Self for method chaining.

        Note
        ----
        The `"*"` wildcard only works with Parser, not JsonParser. For JsonParser,
        explicitly list the fields you want from the enriched JSON structure.

        Example
        -------
        ```python
        # Select specific capture groups
        query.select(["method", "path", "code"])

        # Select all capture groups (Parser only)
        query.select(["*"])

        # Include metadata with capture groups
        query.select(["@log_type", "@log_message", "method", "path"])

        # Combine wildcard with metadata
        query.select(["@log_type", "*"])

        # JsonParser: access nested extracted fields
        query.select(["extracted.user_id", "extracted.action", "message"])
        ```

        """
        if "*" in fields and not self._is_json_parser:
            assert isinstance(self.parser, Parser)
            fields = list(self.parser.get_vars())

        self.fields = fields
        return self

    def select_from(self, source: str | TextIO | BinaryIO | io.StringIO | io.BytesIO) -> Query:
        """
        Alias for from_().

        Args:
            source: Input data to parse. Can be:
                - str: Plain string containing log data
                - TextIO: Text file object (opened in text mode)
                - BinaryIO: Binary file object (opened in binary mode)
                - io.StringIO: String buffer
                - io.BytesIO: Bytes buffer

        Returns:
            Self for method chaining

        """
        return self.from_(source)

    def from_(self, source: str | TextIO | BinaryIO | io.StringIO | io.BytesIO) -> Query:
        """
        Set the input source containing log data.

        Specifies where to read log data from. Must be called before any
        export method (`to_dataframe()`, `to_arrow()`, etc.).

        Args:
            source: Input data to parse. Accepts:

                - `str`: String containing log data
                - `TextIO`: File opened in text mode
                - `BinaryIO`: File opened in binary mode
                - `io.StringIO`: In-memory text stream
                - `io.BytesIO`: In-memory binary stream

        Returns:
            Self for method chaining.

        Raises:
            TypeError: If source type is not supported.

        Note
        ----
        For file objects, the entire content is read into memory. For very
        large files, consider processing in chunks.

        Example
        -------
        ```python
        query = Query(parser).select(["method", "path"])

        # From string
        df = query.from_("GET /api\\nPOST /login").to_dataframe()

        # From file
        with open("access.log") as f:
            df = query.from_(f).to_dataframe()

        # From BytesIO (e.g., from HTTP response)
        import io
        data = io.BytesIO(response.content)
        df = query.from_(data).to_dataframe()
        ```

        """
        # Validate and convert source type
        input_stream: io.StringIO | io.BytesIO
        if isinstance(source, str):
            input_stream = io.StringIO(source)
        elif isinstance(source, (io.StringIO, io.BytesIO)):
            input_stream = source
        elif hasattr(source, "read"):
            # Handle file objects (TextIO or BinaryIO)
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

        self.stream = input_stream
        return self

    def validate_query(self) -> Query:
        """
        Validate that the query is properly configured.

        Returns:
            Self for method chaining

        Raises:
            AttributeError: If fields or stream are not set

        """
        if self.fields is None:
            msg = "Query is missing fields"
            raise AttributeError(msg)
        if not self.fields:
            msg = 'Selected fields must be at least one variable, use "*" if unknown'
            raise AttributeError(msg)
        if self.stream is None:
            msg = "Query is empty"
            raise AttributeError(msg)
        return self

    def to_df(self) -> pd.DataFrame:
        """
        Alias for to_dataframe().

        Returns:
            pandas DataFrame with extracted fields

        """
        return self.to_dataframe()

    def to_dataframe(self) -> pd.DataFrame:
        """
        Export parsed events to a pandas DataFrame.

        Parses all events from the configured source, applies any filter,
        and returns a DataFrame with the selected fields as columns.

        Returns:
            pandas DataFrame with one row per event and one column per
            selected field. Column order matches the order in `select()`.

        Raises:
            ImportError: If pandas is not installed. Install with:
                `pip install 'log-surgeon-ffi[dataframe]'` or `pip install pandas`
            AttributeError: If `select()` or `from_()` was not called.

        Example
        -------
        ```python
        df = (
            Query(parser)
            .select(["method", "path", "code"])
            .from_(log_file)
            .to_dataframe()
        )

        print(df.head())
        #   method       path code
        # 0    GET     /users  200
        # 1   POST     /login  401
        # 2    GET  /products  200

        # Use pandas for analysis
        print(df["code"].value_counts())
        # 200    150
        # 404     23
        # 500      5
        ```

        """
        if pd is None:
            raise ImportError(_DATAFRAME_IMPORT_ERROR)

        rows = self.get_rows()
        return pd.DataFrame(rows, columns=self.fields)

    def to_pa(self) -> pa.Table:
        """
        Alias for to_arrow().

        Returns:
            PyArrow Table with extracted fields

        """
        return self.to_arrow()

    def to_arrow(self) -> pa.Table:
        """
        Export parsed events to a PyArrow Table.

        Parses all events from the configured source, applies any filter,
        and returns a PyArrow Table with the selected fields as columns.
        Arrow Tables are memory-efficient and ideal for large datasets.

        Returns:
            PyArrow Table with one row per event and one column per
            selected field. Column order matches the order in `select()`.

        Raises:
            ImportError: If pyarrow is not installed. Install with:
                `pip install 'log-surgeon-ffi[arrow]'` or `pip install pyarrow`
            AttributeError: If `select()` or `from_()` was not called.

        Note
        ----
        Arrow Tables use columnar storage, which is more memory-efficient
        than row-based formats for large datasets. They also integrate well
        with Parquet files and other data processing tools.

        Example
        -------
        ```python
        table = (
            Query(parser)
            .select(["method", "path", "code"])
            .from_(log_file)
            .to_arrow()
        )

        # Write to Parquet file
        import pyarrow.parquet as pq
        pq.write_table(table, "logs.parquet")

        # Convert to pandas if needed
        df = table.to_pandas()
        ```

        """
        if pa is None:
            raise ImportError(_ARROW_IMPORT_ERROR)

        rows = self.get_rows()
        assert self.fields is not None
        # Transpose rows for column-oriented storage
        columns = [[row[i] for row in rows] for i in range(len(self.fields))]
        return pa.Table.from_arrays([pa.array(col) for col in columns], names=self.fields)

    def get_rows(self) -> list[list[str]]:
        """
        Extract raw rows of field values from parsed events.

        Lower-level method that returns parsed data as a list of lists.
        Each inner list represents one event with values in the order
        specified by `select()`.

        Returns:
            List of rows, where each row is a list of string values.
            Row order matches event order; column order matches `select()` order.

        Note
        ----
        This method is useful when you need raw data without pandas/pyarrow
        dependencies. For most use cases, prefer `to_dataframe()` or `to_arrow()`.

        Example
        -------
        ```python
        query = Query(parser).select(["method", "code"]).from_(log_data)
        rows = query.get_rows()

        for row in rows:
            method, code = row
            print(f"{method} -> {code}")
        ```

        """
        rows: list[list[str]] = []
        assert self.stream is not None
        assert self.fields is not None

        if self._is_json_parser:
            # Handle JsonParser output (dict objects)
            assert isinstance(self.parser, JsonParser)
            for obj in self.parser.parse(self.stream):
                # Apply filter predicate if set
                if self.predicate is not None and not self.predicate(obj):
                    continue

                rows.append([self._get_json_field_value(obj, field) for field in self.fields])
        else:
            # Handle Parser output (LogEvent objects)
            assert isinstance(self.parser, Parser)
            for event in self.parser.parse(self.stream):
                # Apply filter predicate if set
                if self.predicate is not None and not self.predicate(event):
                    continue

                rows.append(
                    [
                        event.get_log_type()
                        if field == "@log_type"
                        else event.get_log_message()
                        if field == "@log_message"
                        else event.get_capture_group_str_representation(field)
                        for field in self.fields
                    ]
                )
        return rows

    def _get_json_field_value(self, obj: dict[str, Any], field: str) -> str:
        """
        Get a field value from a JSON object, supporting dot-notation and nested keys.

        Args:
            obj: JSON dictionary to extract from
            field: Field name or dot-notation path (e.g., "extracted.user_id")

        Returns:
            String representation of the field value

        """
        # Handle dot notation for nested access
        parts = field.split(".")
        current: Any = obj
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return "None"
        return str(current) if current is not None else "None"

    def get_log_types(self) -> Generator[str, None, None]:
        """
        Get unique log types from parsed events.

        Yields each distinct log type template exactly once, in the order
        first encountered. Useful for discovering the different message
        patterns in your logs.

        Yields:
            Unique log type strings (templates with variable placeholders).

        Note
        ----
        - If a filter is set, only matching events contribute log types
        - For JsonParser, requires `include_log_type(True)` to be set
        - Log types are yielded in first-seen order, not sorted

        Example
        -------
        ```python
        query = Query(parser).from_(log_data)

        # Discover all message patterns
        print("Log patterns found:")
        for log_type in query.get_log_types():
            print(f"  {log_type}")

        # Output:
        #   <method> <path> <code>
        #   Connection from <ip>:<port>
        #   Error: <error_message>
        ```

        """
        assert self.stream is not None
        seen_log_types: set[str] = set()

        if self._is_json_parser:
            assert isinstance(self.parser, JsonParser)
            for obj in self.parser.parse(self.stream):
                if self.predicate is not None and not self.predicate(obj):
                    continue
                # Get log type from extracted data
                extracted = obj.get("extracted", {})
                log_type = extracted.get("@log_type")
                if log_type and log_type not in seen_log_types:
                    seen_log_types.add(log_type)
                    yield log_type
        else:
            assert isinstance(self.parser, Parser)
            for event in self.parser.parse(self.stream):
                if self.predicate is not None and not self.predicate(event):
                    continue
                log_type = event.get_log_type()
                if log_type not in seen_log_types:
                    seen_log_types.add(log_type)
                    yield log_type

    def get_log_type_counts(self) -> dict[str, int]:
        """
        Count occurrences of each log type.

        Counts how many times each distinct log type pattern appears in the
        log data. Useful for understanding log composition and identifying
        frequent vs. rare patterns.

        Returns:
            Dictionary mapping log type templates to their occurrence counts.
            Not sorted; use `sorted()` if ordering is needed.

        Note
        ----
        - If a filter is set, only matching events are counted
        - For JsonParser, requires `include_log_type(True)` to be set

        Example
        -------
        ```python
        query = Query(parser).from_(log_data)
        counts = query.get_log_type_counts()

        # Print sorted by frequency (most common first)
        for log_type, count in sorted(counts.items(), key=lambda x: -x[1]):
            print(f"{count:6d}  {log_type}")

        # Output:
        #  15432  <method> <path> <code>
        #   2341  Connection from <ip>:<port>
        #     17  Error: <error_message>

        # Find rare patterns (potential anomalies)
        rare = [lt for lt, c in counts.items() if c < 10]
        print(f"Rare patterns: {len(rare)}")
        ```

        """
        assert self.stream is not None
        log_type_counts: dict[str, int] = {}

        if self._is_json_parser:
            assert isinstance(self.parser, JsonParser)
            for obj in self.parser.parse(self.stream):
                if self.predicate is not None and not self.predicate(obj):
                    continue
                extracted = obj.get("extracted", {})
                log_type = extracted.get("@log_type")
                if log_type:
                    log_type_counts[log_type] = log_type_counts.get(log_type, 0) + 1
        else:
            assert isinstance(self.parser, Parser)
            for event in self.parser.parse(self.stream):
                if self.predicate is not None and not self.predicate(event):
                    continue
                log_type = event.get_log_type()
                log_type_counts[log_type] = log_type_counts.get(log_type, 0) + 1
        return log_type_counts

    def get_log_type_with_sample(self, sample_size: int = 3) -> dict[str, list[str]]:
        """
        Get sample messages for each log type.

        Collects example log messages for each distinct log type pattern.
        Useful for understanding what actual messages match each template
        and for building documentation or debugging patterns.

        Args:
            sample_size: Maximum number of samples to collect per log type.
                Default is 3. Higher values provide more examples but use
                more memory.

        Returns:
            Dictionary mapping log type templates to lists of sample messages.
            Each list contains up to `sample_size` example messages.

        Note
        ----
        - Samples are collected in encounter order (first N seen)
        - If a filter is set, only matching events are sampled
        - For JsonParser with `include_log_type(True)`, samples are JSON strings

        Example
        -------
        ```python
        query = Query(parser).from_(log_data)
        samples = query.get_log_type_with_sample(sample_size=2)

        for log_type, messages in samples.items():
            print(f"Pattern: {log_type}")
            print("Examples:")
            for msg in messages:
                print(f"  {msg}")
            print()

        # Output:
        # Pattern: <method> <path> <code>
        # Examples:
        #   GET /api/users 200
        #   POST /api/login 401
        #
        # Pattern: Connection from <ip>:<port>
        # Examples:
        #   Connection from 192.168.1.1:8080
        #   Connection from 10.0.0.5:3000
        ```

        """
        assert self.stream is not None
        log_type_samples: dict[str, list[str]] = {}

        if self._is_json_parser:
            self._collect_json_samples(log_type_samples, sample_size)
        else:
            self._collect_parser_samples(log_type_samples, sample_size)

        return log_type_samples

    def _collect_json_samples(
        self, log_type_samples: dict[str, list[str]], sample_size: int
    ) -> None:
        """Collect log type samples from JsonParser output."""
        assert isinstance(self.parser, JsonParser)
        assert self.stream is not None
        for obj in self.parser.parse(self.stream):
            if self.predicate is not None and not self.predicate(obj):
                continue
            extracted = obj.get("extracted", {})
            log_type = extracted.get("@log_type")
            if log_type:
                self._add_sample(log_type_samples, log_type, json.dumps(obj), sample_size)

    def _collect_parser_samples(
        self, log_type_samples: dict[str, list[str]], sample_size: int
    ) -> None:
        """Collect log type samples from Parser output."""
        assert isinstance(self.parser, Parser)
        assert self.stream is not None
        for event in self.parser.parse(self.stream):
            if self.predicate is not None and not self.predicate(event):
                continue
            log_type = event.get_log_type()
            self._add_sample(log_type_samples, log_type, event.get_log_message(), sample_size)

    def _add_sample(
        self,
        log_type_samples: dict[str, list[str]],
        log_type: str,
        sample: str,
        sample_size: int,
    ) -> None:
        """Add a sample to the log type samples dict if under the limit."""
        if log_type not in log_type_samples:
            log_type_samples[log_type] = [sample]
        elif len(log_type_samples[log_type]) < sample_size:
            log_type_samples[log_type].append(sample)
