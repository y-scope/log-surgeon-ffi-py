import io
from typing import Generator

from log_surgeon.group_name_resolver import GroupNameResolver
from log_surgeon.schema_builder import SchemaBuilder
from log_surgeon.log_event import LogEvent
from log_surgeon_ffi import ReaderParser

_PARSER_NOT_INITIALIZED_ERROR = (
    "Parser not initialized. Load a log surgeon schema using load_schema() or load_schema_file()"
)


class Parser:
    """
    High-level parser for extracting structured data from unstructured log messages.

    The Parser uses a schema-based approach to identify patterns, extract variables,
    and generate log types from raw log text.
    """

    def __init__(self) -> None:
        """Initialize the parser."""
        self._parser: ReaderParser | None = None
        self._schema_builder: SchemaBuilder = SchemaBuilder()

    def add_var(
        self,
        name: str,
        regex: str,
        hide_var_name_if_named_group_present: bool = True
    ) -> "Parser":
        """
        Add a variable pattern to the parser's schema.

        Args:
            name: Variable name
            regex: Regular expression pattern (supports (?<name>) capture groups)
            hide_var_name_if_named_group_present: If True and capture groups exist,
                hide the variable name from output

        Returns:
            Self for method chaining
        """
        self._schema_builder.add_var(name, regex, hide_var_name_if_named_group_present)
        return self

    def build(self) -> None:
        """
        Build and initialize the parser with the configured schema.

        This method compiles the schema and creates the underlying ReaderParser.
        Must be called after adding variables and before parsing.

        Raises:
            May raise exceptions if schema compilation fails
        """
        self._parser = ReaderParser(
            io.BytesIO(),
            self._schema_builder.build(),
            self._schema_builder.get_capture_group_name_resolver()
        )

    def load_schema(self, schema: str, group_name_resolver: GroupNameResolver) -> None:
        """
        Load a schema string to configure the parser.

        Args:
            schema: Schema definition string
            group_name_resolver: GroupNameResolver for mapping logical to physical group names
        """
        self._parser = ReaderParser(io.BytesIO(), schema, group_name_resolver)

    def parse_event(self, payload: str) -> LogEvent | None:
        """
        Parse a single log event from a string payload.

        Args:
            payload: Log message string to parse

        Returns:
            Parsed LogEvent or None if no event found

        Raises:
            RuntimeError: If parser is not initialized with a schema
        """
        self._ensure_initialized()
        self._parser.reset_input_stream(io.StringIO(payload))
        return self._parser.parse_next_log_event()

    def parse(self, input_stream: io.StringIO | io.BytesIO) -> Generator[LogEvent, None, None]:
        """
        Parse all log events from an input stream.

        Args:
            input_stream: Input stream containing log data (StringIO or BytesIO)

        Yields:
            LogEvent objects for each parsed event

        Raises:
            RuntimeError: If parser is not initialized with a schema

        Example:
            >>> parser = Parser()
            >>> parser.load_schema(schema, resolver)
            >>> with open("logs.txt") as f:
            ...     for event in parser.parse(io.StringIO(f.read())):
            ...         print(event['field_name'])
        """
        self._ensure_initialized()
        self._parser.reset_input_stream(input_stream)
        while (event := self._parser.parse_next_log_event()) is not None:
            yield event

    def _ensure_initialized(self) -> None:
        """
        Ensure the parser has been initialized with a schema.

        Raises:
            RuntimeError: If parser is not initialized
        """
        if self._parser is None:
            raise RuntimeError(_PARSER_NOT_INITIALIZED_ERROR)


if __name__ == "__main__":
    # Example 1: Extract a single capture group from a log message
    parser = Parser()
    parser.add_var(
        "memoryStore",
        r"MemoryStore started with capacity (?<memory_store_capacity_GiB>\d+\.\d+) GiB"
    )
    parser.build()

    event = parser.parse_event(
        " INFO [main] MemoryStore: MemoryStore started with capacity 7.0 GiB\n"
    )

    print("Example 1: Basic parsing")
    print(f"Message: {event.get_log_message().strip()}")
    print(f"LogType: {event.get_log_type()}")
    print(f"Capture groups: {event}")
    print()

    # Example 2: Extract multiple capture groups (platform metadata + application data)
    parser = Parser()
    parser.add_var(
        "platform",
        r"(?<platform_level>(INFO)|(WARN)|(ERROR)) \[(?<platform_thread>.+)\] (?<platform_component>.+):"
    )
    parser.add_var(
        "memoryStore",
        r"MemoryStore started with capacity (?<memory_store_capacity_GiB>\d+\.\d+) GiB"
    )
    parser.build()

    event = parser.parse_event(
        " INFO [main] MemoryStore: MemoryStore started with capacity 7.0 GiB\n"
    )

    print("Example 2: Multiple capture groups")
    print(f"Message: {event.get_log_message().strip()}")
    print(f"LogType: {event.get_log_type()}")
    print(f"Capture groups: {event}")
