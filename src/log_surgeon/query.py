import io
from typing import TYPE_CHECKING

from log_surgeon.log_event import LogEvent
from log_surgeon.parser import Parser

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
    """Query builder for parsing log events into structured data formats."""

    def __init__(self, parser: Parser) -> None:
        self.fields: list[str] | None = None
        self.stream: io.StringIO | io.BytesIO | None = None
        self.parser: Parser = parser

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
        if "*" in fields and len(fields) > 1:
            raise AttributeError('You cannot combine "*" with other field names.')

        self.fields = fields
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
            raise AttributeError('Query is missing fields')
        if not self.fields:
            raise AttributeError('Selected fields must be at least one variable, use "*" if unknown')
        if self.stream is None:
            raise AttributeError('Query is empty')
        return self

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
            return pd.json_normalize(self.parser.parse(self.stream))

        rows = self.get_rows(drop_null_rows)
        return pd.DataFrame(rows, columns=self.fields)

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
            records = list(self.parser.parse(self.stream))
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
            row = [event.get_variable_str(field) for field in self.fields]
            if not drop_null_rows or not all(value is None for value in row):
                rows.append(row)
        return rows

if __name__ == '__main__':
    from log_surgeon.schema_builder import SchemaBuilder

    schema_builder = SchemaBuilder()
    schema_builder.add_var(
        "MemoryStore",
        r"MemoryStore started with capacity (?<MemoryStoreCapacityGiB>\d+\.\d+) GiB"
    )
    parser = Parser(schema_builder.compile())

    input_stream = io.StringIO(" INFO [main] MemoryStore: MemoryStore started with capacity 7.0 GiB\n")
    query = (
        Query(parser)
        .select(["MemoryStoreCapacityGiB"])
        .from_stream(input_stream)
        .validate_query()
    )

    df = query.to_dataframe(drop_null_rows=True)
    arrow_table = query.to_arrow(drop_null_rows=True)

    print("Query executed successfully")