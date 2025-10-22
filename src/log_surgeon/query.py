import io
from typing import TYPE_CHECKING, TextIO, BinaryIO, Callable

from log_surgeon.parser import Parser
from log_surgeon.log_event import LogEvent

if TYPE_CHECKING:
    import pandas as pd
    import pyarrow as pa

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
    "Install it with: pip install log-surgeon-ffi[dataframe]"
)

_ARROW_IMPORT_ERROR = (
    "pyarrow is required for this operation. "
    "Install it with: pip install log-surgeon-ffi[dataframe]"
)


class Query:
    """
    Query builder for parsing log events into structured data formats.

    The Query class provides a fluent interface for extracting structured data
    from log files. It supports exporting to pandas DataFrames and PyArrow Tables.

    Example:
        >>> parser = Parser()
        >>> parser.add_var("metric", r"value=(?<value>\\d+)")
        >>> parser.compile()
        >>> query = Query(parser).select(["value"]).from_stream(stream)
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

    def filter(self, predicate: Callable[[LogEvent], bool]) -> "Query":
        """
        Filter log events using a predicate function.

        Args:
            predicate: Function that takes a LogEvent and returns True to include it,
                      False to exclude it from results

        Returns:
            Self for method chaining

        Example:
            >>> # Filter by field value
            >>> query.filter(lambda event: int(event['value']) > 50)
            >>>
            >>> # Filter by multiple conditions
            >>> query.filter(lambda event: event['level'] == 'ERROR' and 'exception' in event.get_log_message())
            >>>
            >>> # Filter with try/catch for missing fields
            >>> def has_high_cpu(event):
            ...     try:
            ...         return int(event['cpu_usage']) > 80
            ...     except (KeyError, ValueError):
            ...         return False
            >>> query.filter(has_high_cpu)
        """
        self.predicate = predicate
        return self

    def select(self, fields: list[str]) -> "Query":
        """
        Select fields to extract from log events.

        Args:
            fields: List of field names, or ["*"] for all fields

        Returns:
            Self for method chaining

        Raises:
            AttributeError: If "*" is combined with other field names
        """
        if "*" in fields:
            if len(fields) > 1:
                raise AttributeError("You cannot combine \"*\" with other field names.")
            fields = list(self.parser.get_vars())

        self.fields = fields
        return self

    def select_from(self, input: str | TextIO | BinaryIO | io.StringIO | io.BytesIO) -> "Query":
        """
        Alias for from_().

        Args:
            input: Input data to parse. Can be:
                - str: Plain string containing log data
                - TextIO: Text file object (opened in text mode)
                - BinaryIO: Binary file object (opened in binary mode)
                - io.StringIO: String buffer
                - io.BytesIO: Bytes buffer

        Returns:
            Self for method chaining
        """
        return self.from_(input)

    def from_(self, input: str | TextIO | BinaryIO | io.StringIO | io.BytesIO) -> "Query":
        """
        Set the input source to parse.

        Args:
            input: Input data to parse. Can be:
                - str: Plain string containing log data
                - TextIO: Text file object (opened in text mode)
                - BinaryIO: Binary file object (opened in binary mode)
                - io.StringIO: String buffer
                - io.BytesIO: Bytes buffer

        Returns:
            Self for method chaining

        Raises:
            TypeError: If input type is not supported

        Example:
            >>> query = Query(parser).select(["value"])
            >>> query.from_("log data here")
            >>> # Or from file
            >>> with open("logs.txt", "r") as f:
            ...     query.from_(f)
        """
        # Validate and convert input type
        if isinstance(input, str):
            input_stream = io.StringIO(input)
        elif isinstance(input, (io.StringIO, io.BytesIO)):
            input_stream = input
        elif hasattr(input, "read"):
            # Handle file objects (TextIO or BinaryIO)
            content = input.read()
            if isinstance(content, bytes):
                input_stream = io.BytesIO(content)
            elif isinstance(content, str):
                input_stream = io.StringIO(content)
            else:
                raise TypeError(
                    f"File object returned unsupported type {type(content).__name__}"
                )
        else:
            raise TypeError(
                f"Input must be str, file object, io.StringIO, or io.BytesIO, "
                f"got {type(input).__name__}"
            )

        self.stream = input_stream
        return self

    def from_stream(self, stream: io.StringIO | io.BytesIO) -> "Query":
        """
        Set the input stream to parse.

        Args:
            stream: Input stream containing log data

        Returns:
            Self for method chaining
        """
        self.stream = stream
        return self

    def validate_query(self) -> "Query":
        """
        Validate that the query is properly configured.

        Returns:
            Self for method chaining

        Raises:
            AttributeError: If fields or stream are not set
        """
        if self.fields is None:
            raise AttributeError("Query is missing fields")
        if not self.fields:
            raise AttributeError("Selected fields must be at least one variable, use \"*\" if unknown")
        if self.stream is None:
            raise AttributeError("Query is empty")
        return self

    def to_df(self, drop_null_rows: bool = True) -> "pd.DataFrame":
        """
        Alias for to_dataframe().

        Args:
            drop_null_rows: Whether to drop rows with all null values

        Returns:
            pandas DataFrame with extracted fields
        """
        return self.to_dataframe(drop_null_rows=drop_null_rows)

    def to_dataframe(self, drop_null_rows: bool = True) -> "pd.DataFrame":
        """
        Convert parsed events to a pandas DataFrame.

        Args:
            drop_null_rows: Whether to drop rows with all null values

        Returns:
            pandas DataFrame with extracted fields

        Raises:
            ImportError: If pandas is not installed
        """
        if pd is None:
            raise ImportError(_DATAFRAME_IMPORT_ERROR)

        if self.fields and self.fields[0] == "*":
            events = self.parser.parse(self.stream)
            # Apply filter if set
            if self.predicate is not None:
                events = (event for event in events if self.predicate(event))
            return pd.json_normalize(events)

        rows = self.get_rows(drop_null_rows)
        return pd.DataFrame(rows, columns=self.fields)

    def to_pa(self, drop_null_rows: bool = True) -> "pa.Table":
        """
        Alias for to_arrow().

        Args:
            drop_null_rows: Whether to drop rows with all null values

        Returns:
            PyArrow Table with extracted fields
        """
        return self.to_arrow(drop_null_rows=drop_null_rows)

    def to_arrow(self, drop_null_rows: bool = True) -> "pa.Table":
        """
        Convert parsed events to a PyArrow Table.

        Args:
            drop_null_rows: Whether to drop rows with all null values

        Returns:
            PyArrow Table with extracted fields

        Raises:
            ImportError: If pyarrow is not installed
        """
        if pa is None:
            raise ImportError(_ARROW_IMPORT_ERROR)

        if self.fields and self.fields[0] == "*":
            events = self.parser.parse(self.stream)
            # Apply filter if set
            if self.predicate is not None:
                events = (event for event in events if self.predicate(event))
            records = list(events)
            return pa.Table.from_pylist(records)

        rows = self.get_rows(drop_null_rows)
        # Transpose rows for column-oriented storage
        columns = [[row[i] for row in rows] for i in range(len(self.fields))]
        return pa.Table.from_arrays([pa.array(col) for col in columns], names=self.fields)

    def get_rows(self, drop_null_rows: bool = True) -> list[list]:
        """
        Extract rows of field values from parsed events.

        Args:
            drop_null_rows: Whether to skip rows with all null values

        Returns:
            List of rows, where each row is a list of field values
        """
        rows = []
        for event in self.parser.parse(self.stream):
            # Apply filter predicate if set
            if self.predicate is not None and not self.predicate(event):
                continue

            row = [event.get_capture_group_str_representation(field) for field in self.fields]
            if not drop_null_rows or not all(value is None for value in row):
                rows.append(row)
        return rows

if __name__ == "__main__":
    # Example: Extract metrics from logs and export to DataFrame
    parser = Parser()
    parser.add_var(
        "memoryStore",
        r"MemoryStore started with capacity (?<memory_store_capacity_GiB>\d+\.\d+) GiB"
    )
    parser.compile()

    log_data = " INFO [main] MemoryStore: MemoryStore started with capacity 7.0 GiB"

    query = (
        Query(parser)
        .select(["memory_store_capacity_GiB"])
        .from_stream(log_data)
        .validate_query()
    )

    # Export to pandas DataFrame
    df = query.to_dataframe(drop_null_rows=True)
    print("DataFrame:")
    print(df)
    print()

    # Reset stream for second export
    query.from_stream(log_data)

    # Export to PyArrow Table
    arrow_table = query.to_arrow(drop_null_rows=True)
    print("Arrow Table:")
    print(arrow_table)