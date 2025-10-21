import io
from pathlib import Path
from typing import Generator

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

    def __init__(self, schema: str | None = None) -> None:
        """
        Initialize the parser with an optional schema.

        Args:
            schema: Optional schema string. If provided, parser is ready to use immediately
        """
        self._parser: ReaderParser | None = None
        if schema:
            self.load_schema(schema)

    def load_schema_file(self, schema_file_path: str | Path) -> None:
        """
        Load a schema from a file.

        Args:
            schema_file_path: Path to the schema file

        Raises:
            FileNotFoundError: If the schema file doesn't exist
            IOError: If there's an error reading the file
        """
        path = Path(schema_file_path)
        with path.open("r", encoding="utf-8") as schema_file:
            self.load_schema(schema_file.read())

    def load_schema(self, schema: str) -> None:
        """
        Load a schema string to configure the parser.

        Args:
            schema: Schema definition string
        """
        self._parser = ReaderParser(io.BytesIO(), schema)

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
    parser.load_schema(schema_builder.build())

    # Before we parse anything, log-surgeon will jit-compile a model similar to re.compile
    event = parser.parse_event(" INFO [main] MemoryStore: MemoryStore started with capacity 7.0 GiB\n")

    # Log-surgeon identifies and labels and extracts the variables in unstructured text, no matter where it is,
    # and also generates
    print("#######################################################")
    print(f"Message: {event.get_log_message().strip()}")
    print(f"\t@LogType -> {event.get_log_type(schema_builder.get_capture_group_name_resolver())}")
    print(f"\tmemory_store_capacity_GiB -> {event.get_capture_group('memory_store_capacity_GiB', schema_builder.get_capture_group_name_resolver())}")

    # Let's iterate on this example log and extract 3 platform variables: level, thread, component
    schema_builder.add_var("platform",
                           r"(?<platform_level>(INFO)|(WARN)|(ERROR)) \[(?<platform_thread>.+)\] (?<platform_component>.+):")
    parser.load_schema(schema_builder.build())
    event = parser.parse_event(" INFO [main] MemoryStore: MemoryStore started with capacity 7.0 GiB\n")
    print("#######################################################")
    print(f"Message: {event.get_log_message().strip()}")
    print(f"\t@LogType -> {event.get_log_type(schema_builder.get_capture_group_name_resolver())}")
    print(f"\tplatform_level -> {event.get_capture_group('platform_level', schema_builder.get_capture_group_name_resolver())}")
    print(f"\tplatform_thread -> {event.get_capture_group('platform_thread', schema_builder.get_capture_group_name_resolver())}")
    print(f"\tplatform_component -> {event.get_capture_group('platform_component', schema_builder.get_capture_group_name_resolver())}")
    print(f"\tmemory_store_capacity_GiB -> {event.get_capture_group('memory_store_capacity_GiB', schema_builder.get_capture_group_name_resolver())}")
