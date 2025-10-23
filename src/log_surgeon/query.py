"""
Query builder for extracting and exporting structured log data.

This module provides the Query class, which offers a fluent interface for:
- Selecting specific fields from parsed log events
- Filtering events with custom predicates
- Exporting results to pandas DataFrames or PyArrow Tables
- Analyzing log types and patterns

The Query class works with Parser instances to transform raw log data into
structured formats suitable for analysis and data science workflows.
"""

from __future__ import annotations

import io
from typing import BinaryIO, Callable, TextIO, TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Generator

    import pandas as pd  # type: ignore[import-untyped]
    import pyarrow as pa  # type: ignore[import-untyped]

    from log_surgeon.log_event import LogEvent

from log_surgeon.parser import Parser  # noqa: TC001 - Parser is used at runtime

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

    The Query class provides a fluent interface for extracting structured data
    from log files. It supports exporting to pandas DataFrames and PyArrow Tables.

    Example:
        >>> parser = Parser()
        >>> parser.add_var("metric", r"value=(?<value>\\d+)")
        >>> parser.compile()
        >>> query = Query(parser).select(["value"]).from_(log_data)
        >>> df = query.to_dataframe()

    """

    def __init__(self, parser: Parser) -> None:
        """
        Initialize a query builder.

        Args:
            parser: Configured Parser instance for log parsing

        """
        self.fields: list[str] | None = None
        self.stream: io.StringIO | io.BytesIO | None = None
        self.parser: Parser = parser
        self.predicate: Callable[[LogEvent], bool] | None = None

    def filter(self, predicate: Callable[[LogEvent], bool]) -> Query:
        """
        Filter log events using a predicate function.

        Note:
            Cannot be chained - calling filter() multiple times will replace the
            previous predicate. Only the most recently set predicate is applied.
            To apply multiple conditions, combine them in a single predicate using
            `and`/`or` operators.

        Args:
            predicate: Function that takes a LogEvent and returns True to include it,
                      False to exclude it from results

        Returns:
            Self for method chaining

        Example:
            >>> # Filter by field value
            >>> query.filter(lambda event: int(event["value"]) > 50)
            >>>
            >>> # Filter by multiple conditions (combine with 'and'/'or')
            >>> query.filter(lambda event: event["level"] == "ERROR" and "exception" in str(event))
            >>>
            >>> # Filter with try/catch for missing fields
            >>> def has_high_cpu(event):
            ...     try:
            ...         return int(event["cpu_usage"]) > 80
            ...     except (KeyError, ValueError):
            ...         return False
            >>> query.filter(has_high_cpu)

        """
        self.predicate = predicate
        return self

    def select(self, fields: list[str]) -> Query:
        """
        Select fields to extract from log events.

        Args:
            fields: List of field names to extract. Supports:
                - Variable names defined in the schema (e.g., "user_id", "value")
                - "*" to select all variables defined in the schema
                - "@log_type" to include the generated log type (template)
                - "@log_message" to include the original log message

        Returns:
            Self for method chaining

        Example:
            >>> # Select specific variables
            >>> query.select(["user_id", "value"])
            >>>
            >>> # Select all variables
            >>> query.select(["*"])
            >>>
            >>> # Include log type and message with variables
            >>> query.select(["@log_type", "@log_message", "user_id", "value"])
            >>>
            >>> # Expand all variables and include metadata
            >>> query.select(["@log_type", "@log_message", "*"])

        """
        if "*" in fields:
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
        Set the input source to parse.

        Args:
            source: Input data to parse. Can be:
                - str: Plain string containing log data
                - TextIO: Text file object (opened in text mode)
                - BinaryIO: Binary file object (opened in binary mode)
                - io.StringIO: String buffer
                - io.BytesIO: Bytes buffer

        Returns:
            Self for method chaining

        Raises:
            TypeError: If source type is not supported

        Example:
            >>> query = Query(parser).select(["value"])
            >>> query.from_("log data here")
            >>> # Or from file
            >>> with open("logs.txt", "r") as f:
            ...     query.from_(f)

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
        Convert parsed events to a pandas DataFrame.

        Returns:
            pandas DataFrame with extracted fields

        Raises:
            ImportError: If pandas is not installed

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
        Convert parsed events to a PyArrow Table.

        Returns:
            PyArrow Table with extracted fields

        Raises:
            ImportError: If pyarrow is not installed

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
        Extract rows of field values from parsed events.

        Returns:
            List of rows, where each row is a list of field values

        """
        rows: list[list[str]] = []
        assert self.stream is not None
        assert self.fields is not None
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

    def get_log_types(self) -> Generator[str, None, None]:
        """
        Get all unique log types from the parsed events.

        Yields log types in the order they are first encountered.
        If a filter predicate is set, only events matching the filter are included.

        Yields:
            Unique log type strings (templates) from parsed events

        Example:
            >>> query = Query(parser).from_(log_data)
            >>> for log_type in query.get_log_types():
            ...     print(log_type)
            <timestamp> INFO: Processing <metric>
            <timestamp> WARN: Error in <component>

        """
        assert self.stream is not None
        seen_log_types: set[str] = set()
        for event in self.parser.parse(self.stream):
            # Apply filter predicate if set
            if self.predicate is not None and not self.predicate(event):
                continue

            log_type = event.get_log_type()
            if log_type not in seen_log_types:
                seen_log_types.add(log_type)
                yield log_type

    def get_log_type_counts(self) -> dict[str, int]:
        """
        Get count of occurrences for each unique log type.

        If a filter predicate is set, only events matching the filter are counted.

        Returns:
            Dictionary mapping log types to their occurrence counts

        Example:
            >>> query = Query(parser).from_(log_data)
            >>> counts = query.get_log_type_counts()
            >>> for log_type, count in counts.items():
            ...     print(f"{count:5d} {log_type}")
                42 <timestamp> INFO: Processing <metric>
                 7 <timestamp> WARN: Error in <component>

        """
        assert self.stream is not None
        log_type_counts: dict[str, int] = {}
        for event in self.parser.parse(self.stream):
            # Apply filter predicate if set
            if self.predicate is not None and not self.predicate(event):
                continue

            log_type = event.get_log_type()
            log_type_counts[log_type] = log_type_counts.get(log_type, 0) + 1
        return log_type_counts

    def get_log_type_with_sample(self, sample_size: int = 3) -> dict[str, list[str]]:
        """
        Get sample log messages for each unique log type.

        Collects up to `sample_size` example messages for each log type encountered.
        Useful for understanding what actual log messages match each template.
        If a filter predicate is set, only events matching the filter are sampled.

        Args:
            sample_size: Maximum number of sample messages to collect per log type.
                Default is 3.

        Returns:
            Dictionary mapping log types to lists of sample log messages

        Example:
            >>> query = Query(parser).from_(log_data)
            >>> samples = query.get_log_type_with_sample(sample_size=2)
            >>> for log_type, messages in samples.items():
            ...     print(f"Log Type: {log_type}")
            ...     for msg in messages:
            ...         print(f"  - {msg}")
            Log Type: <timestamp> INFO: Processing <metric>
              - 2024-01-01 INFO: Processing value=42
              - 2024-01-01 INFO: Processing value=100

        """
        assert self.stream is not None
        log_type_samples: dict[str, list[str]] = {}
        for event in self.parser.parse(self.stream):
            # Apply filter predicate if set
            if self.predicate is not None and not self.predicate(event):
                continue

            log_type = event.get_log_type()

            # Initialize list for new log types or append if under sample size
            if log_type not in log_type_samples:
                log_type_samples[log_type] = [event.get_log_message()]
            elif len(log_type_samples[log_type]) < sample_size:
                log_type_samples[log_type].append(event.get_log_message())

        return log_type_samples
