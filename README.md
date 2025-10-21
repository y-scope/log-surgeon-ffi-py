# log-surgeon-ffi

Python FFI bindings for [log-surgeon](https://github.com/y-scope/log-surgeon), a high-performance library for parsing unstructured log messages into structured data.

## Overview

log-surgeon-ffi provides a Pythonic interface to the log-surgeon C++ library, enabling efficient extraction of structured information from unstructured log files. It uses schema-based pattern matching to:

- **Extract variables** from log messages using regex patterns with named capture groups
- **Generate log types** (templates) automatically for log analysis
- **Parse streams** efficiently for large-scale log processing
- **Export data** to pandas DataFrames and PyArrow Tables

## Installation

```bash
pip install log-surgeon-ffi
```

For optional DataFrame/Arrow support:
```bash
pip install log-surgeon-ffi[dataframe]
```

## Quick Start

### Basic Parsing

```python
import io
from log_surgeon import Parser

# Create a parser and define extraction patterns
parser = Parser()
parser.add_var(
    "memoryStore",
    r"MemoryStore started with capacity (?<memory_store_capacity_GiB>\d+\.\d+) GiB"
)
parser.build()

# Parse a log event
log_line = " INFO [main] MemoryStore: MemoryStore started with capacity 7.0 GiB\n"
event = parser.parse_event(log_line)

# Access extracted data
print(f"Message: {event.get_log_message()}")
print(f"LogType: {event.get_log_type()}")
print(f"Capacity: {event['memory_store_capacity_GiB']}")
```

### Multiple Capture Groups

```python
parser = Parser()

# Extract platform information (level, thread, component)
parser.add_var(
    "platform",
    r"(?<platform_level>(INFO)|(WARN)|(ERROR)) \[(?<platform_thread>.+)\] (?<platform_component>.+):"
)

# Extract application-specific metrics
parser.add_var(
    "memoryStore",
    r"MemoryStore started with capacity (?<memory_store_capacity_GiB>\d+\.\d+) GiB"
)

parser.build()

event = parser.parse_event(" INFO [main] MemoryStore: MemoryStore started with capacity 7.0 GiB\n")

print(f"Level: {event['platform_level']}")
print(f"Thread: {event['platform_thread']}")
print(f"Component: {event['platform_component']}")
print(f"Capacity: {event['memory_store_capacity_GiB']}")
```

### Stream Parsing

```python
import io
from log_surgeon import Parser

parser = Parser()
parser.add_var("metric", r"value=(?<value>\d+)")
parser.build()

# Parse multiple events from a stream
log_data = """
2024-01-01 INFO: Processing metric value=42
2024-01-01 INFO: Processing metric value=100
2024-01-01 INFO: Processing metric value=7
"""

for event in parser.parse(io.StringIO(log_data)):
    print(f"Value: {event['value']}")
```

### Export to DataFrame

```python
import io
from log_surgeon import Parser, Query

parser = Parser()
parser.add_var(
    "metric",
    r"metric=(?<metric_name>\w+) value=(?<value>\d+)"
)
parser.build()

log_data = """
2024-01-01 INFO: metric=cpu value=42
2024-01-01 INFO: metric=memory value=100
2024-01-01 INFO: metric=disk value=7
"""

# Create a query and export to DataFrame
query = (
    Query(parser)
    .select(["metric_name", "value"])
    .from_stream(io.StringIO(log_data))
    .validate_query()
)

df = query.to_dataframe()
print(df)
```

## API Reference

### Parser

High-level parser for extracting structured data from unstructured log messages.

#### Methods

- `add_var(name: str, regex: str, hide_var_name_if_named_group_present: bool = True) -> Parser`
  - Add a variable pattern to the parser's schema
  - Supports named capture groups using `(?<name>)` syntax
  - Returns self for method chaining

- `build() -> None`
  - Build and initialize the parser with the configured schema
  - Must be called after adding variables and before parsing

- `load_schema(schema: str, group_name_resolver: GroupNameResolver) -> None`
  - Load a pre-built schema string to configure the parser

- `parse_event(payload: str) -> LogEvent | None`
  - Parse a single log event from a string
  - Returns LogEvent or None if no event found

- `parse(input_stream: io.StringIO | io.BytesIO) -> Generator[LogEvent, None, None]`
  - Parse all log events from an input stream
  - Yields LogEvent objects for each parsed event

### LogEvent

Represents a parsed log event with extracted variables.

#### Methods

- `get_log_message() -> str`
  - Get the original log message

- `get_log_type() -> str`
  - Get the generated log type (template)

- `get_capture_group_str_representation(field: str) -> str | None`
  - Get the string representation of a capture group value

- `__getitem__(key: str) -> str`
  - Access capture group values by name (e.g., `event['field_name']`)

### Query

Query builder for parsing log events into structured data formats.

#### Methods

- `select(fields: list[str]) -> Query`
  - Select fields to extract (use `["*"]` for all fields)

- `from_stream(stream: io.StringIO | io.BytesIO) -> Query`
  - Set the input stream to parse

- `validate_query() -> Query`
  - Validate that the query is properly configured

- `to_dataframe(drop_null_rows: bool = True) -> pd.DataFrame`
  - Convert parsed events to a pandas DataFrame

- `to_arrow(drop_null_rows: bool = True) -> pa.Table`
  - Convert parsed events to a PyArrow Table

### SchemaBuilder

Builder for constructing log-surgeon schema definitions.

#### Methods

- `add_var(name: str, regex: str, hide_var_name_if_named_group_present: bool = True) -> SchemaBuilder`
  - Add a variable pattern to the schema

- `add_timestamp(name: str, regex: str) -> SchemaBuilder`
  - Add a timestamp pattern to the schema

- `build() -> str`
  - Build the final schema string

- `get_capture_group_name_resolver() -> GroupNameResolver`
  - Get the resolver for mapping logical to physical capture group names

## Schema Format

The schema defines delimiters, timestamps, and variables for parsing:

```
// schema delimiters
delimiters: \t\r\n:,!;%@/\(\)\[\]

// schema timestamps
timestamp:<timestamp_regex>

// schema variables
variable_name:<variable_regex>
```

Named capture groups in regex patterns use the syntax `(?<name>pattern)`.

## Development

### Building from Source

```bash
# Clone the repository
git clone https://github.com/y-scope/log-surgeon-ffi-py.git
cd log-surgeon-ffi-py

# Install development dependencies
pip install -e ".[dev]"

# Build the extension
cmake -S . -B build
cmake --build build
```

### Running Tests

```bash
python -m pytest tests/
```

## Requirements

- Python >= 3.9
- C++17 compatible compiler

## License

Apache License 2.0 - See [LICENSE](LICENSE) for details.

## Links

- [Homepage](https://github.com/y-scope/log-surgeon-ffi-py)
- [Bug Tracker](https://github.com/y-scope/log-surgeon-ffi-py/issues)
- [log-surgeon C++ library](https://github.com/y-scope/log-surgeon)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
