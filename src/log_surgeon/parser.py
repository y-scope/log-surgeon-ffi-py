import io
from pathlib import Path
from typing import Generator

from log_surgeon.group_name_resolver import GroupNameResolver
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
        """
        Initialize the parser with an optional schema.
        """
        self._parser: ReaderParser | None = None


    def load_schema(self, schema: str, group_name_resolver: GroupNameResolver) -> None:
        """
        Load a schema string to configure the parser.

        Args:
            schema: Schema definition string
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
            >>> parser = Parser(schema)
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



if __name__ == '__main__':
    from log_surgeon.schema_builder import SchemaBuilder

    parser = Parser()

    # Begin with a basic motivating example: " INFO [main] MemoryStore: MemoryStore started with capacity 7.0 GiB\n"
    # 1. Extract the numeric value "7.0" from the log
    # 2. Assign it the label "MemoryStoreCapacityGiB"
    # 3. Generate log type (template)

    # We can achieve this easily using log surgeon
    # The first step is to specify the schema used for labeling, extraction and templating
    # We define a variable name, and a regular expression with a named capture group.
    schema_builder = SchemaBuilder()
    schema_builder.add_var("memoryStore",
                           "MemoryStore started with capacity (?<memory_store_capacity_GiB>\d+\.\d+) GiB")
    parser.load_schema(schema_builder.build(), schema_builder.get_capture_group_name_resolver())

    # Before we parse anything, log-surgeon will jit-compile a model similar to re.compile
    event = parser.parse_event(" INFO [main] MemoryStore: MemoryStore started with capacity 7.0 GiB\n")

    # Log-surgeon identifies and labels and extracts the variables in unstructured text, no matter where it is,
    # and also generates
    print("#######################################################")
    print(f"Message: {event.get_log_message().strip()}")
    print(f"LogType -> {event.get_log_type()}")
    print(f"Capture groups -> {event}")

    # Let's iterate on this example log and extract 3 platform variables: level, thread, component
    schema_builder.add_var("platform",
                           r"(?<platform_level>(INFO)|(WARN)|(ERROR)) \[(?<platform_thread>.+)\] (?<platform_component>.+):")
    parser.load_schema(schema_builder.build(), schema_builder.get_capture_group_name_resolver())
    event = parser.parse_event(" INFO [main] MemoryStore: MemoryStore started with capacity 7.0 GiB\n")
    print("#######################################################")
    print(f"Message: {event.get_log_message().strip()}")
    print(f"LogType -> {event.get_log_type()}")
    print(f"Capture groups -> {event}")
