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
parser.compile()

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

parser.compile()

event = parser.parse_event(" INFO [main] MemoryStore: MemoryStore started with capacity 7.0 GiB\n")

print(f"Level: {event['platform_level']}")
print(f"Thread: {event['platform_thread']}")
print(f"Component: {event['platform_component']}")
print(f"Capacity: {event['memory_store_capacity_GiB']}")
```

### Stream Parsing

```python
from log_surgeon import Parser

parser = Parser()
parser.add_var("metric", r"value=(?<value>\d+)")
parser.compile()

# Parse from string (automatically wrapped in StringIO)
log_data = """
2024-01-01 INFO: Processing metric value=42
2024-01-01 INFO: Processing metric value=100
2024-01-01 INFO: Processing metric value=7
"""

for event in parser.parse(log_data):
  print(f"Value: {event['value']}")

# Or parse from file object directly
with open("logs.txt", "r") as f:
  for event in parser.parse(f):
    print(f"Value: {event['value']}")
```

### Using Pattern Constants

```python
from log_surgeon import Parser, Pattern

parser = Parser()
parser.add_var("network", rf"IP: (?<ip>{Pattern.IPV4}) UUID: (?<id>{Pattern.UUID})")
parser.add_var("metrics", rf"value=(?<value>{Pattern.FLOAT})")
parser.compile()

log_line = "IP: 192.168.1.1 UUID: 550e8400-e29b-41d4-a716-446655440000 value=42.5"
event = parser.parse_event(log_line)

print(f"IP: {event['ip']}")
print(f"UUID: {event['id']}")
print(f"Value: {event['value']}")
```

### Export to DataFrame

```python
from log_surgeon import Parser, Query

parser = Parser()
parser.add_var(
  "metric",
  r"metric=(?<metric_name>\w+) value=(?<value>\d+)"
)
parser.compile()

log_data = """
2024-01-01 INFO: metric=cpu value=42
2024-01-01 INFO: metric=memory value=100
2024-01-01 INFO: metric=disk value=7
"""

# Create a query and export to DataFrame
query = (
  Query(parser)
  .select(["metric_name", "value"])
  .from_(log_data)
  .validate_query()
)

df = query.to_dataframe()
print(df)
```

### Filtering Events

```python
from log_surgeon import Parser, Query

parser = Parser()
parser.add_var("metric", r"metric=(?<metric_name>\w+) value=(?<value>\d+)")
parser.compile()

log_data = """
2024-01-01 INFO: metric=cpu value=42
2024-01-01 INFO: metric=memory value=100
2024-01-01 INFO: metric=disk value=7
2024-01-01 INFO: metric=cpu value=85
"""

# Filter events where value > 50
query = (
  Query(parser)
  .select(["metric_name", "value"])
  .from_(log_data)
  .filter(lambda event: int(event['value']) > 50)
  .validate_query()
)

df = query.to_dataframe()
print(df)
# Output:
#   metric_name  value
# 0      memory    100
# 1         cpu     85
```

### Including Log Metadata

Use special fields `@log_type` and `@log_message` to include log metadata alongside extracted variables:

```python
from log_surgeon import Parser, Query

parser = Parser()
parser.add_var("metric", r"value=(?<value>\d+)")
parser.compile()

log_data = """
2024-01-01 INFO: Processing value=42
2024-01-01 WARN: Processing value=100
"""

# Select log type, message, and all variables
query = (
  Query(parser)
  .select(["@log_type", "@log_message", "*"])
  .from_(log_data)
  .validate_query()
)

df = query.to_dataframe()
print(df)
# Output:
#                          @log_type                         @log_message value
# 0  <timestamp> INFO: Processing <metric>  2024-01-01 INFO: Processing value=42    42
# 1  <timestamp> WARN: Processing <metric>  2024-01-01 WARN: Processing value=100  100
```

The `"*"` wildcard expands to all variables defined in the schema and can be combined with other fields like `@log_type` and `@log_message`.

## API Reference

### Parser

High-level parser for extracting structured data from unstructured log messages.

#### Constructor

- `Parser(delimiters: str = r" \t\r\n:,!;%@/\(\)\[\]")`
  - Initialize a parser with optional custom delimiters
  - Default delimiters include space, tab, newline, and common punctuation

#### Methods

- `add_var(name: str, regex: str, hide_var_name_if_named_group_present: bool = True) -> Parser`
  - Add a variable pattern to the parser's schema
  - Supports named capture groups using `(?<name>)` syntax
  - Returns self for method chaining

- `add_timestamp(name: str, regex: str) -> Parser`
  - Add a timestamp pattern to the parser's schema
  - Returns self for method chaining

- `compile(enable_debug_logs: bool = False) -> None`
  - Build and initialize the parser with the configured schema
  - Must be called after adding variables and before parsing
  - Set `enable_debug_logs=True` to output debug information to stderr

- `load_schema(schema: str, group_name_resolver: GroupNameResolver) -> None`
  - Load a pre-built schema string to configure the parser

- `parse(input: str | TextIO | BinaryIO | io.StringIO | io.BytesIO) -> Generator[LogEvent, None, None]`
  - Parse all log events from a string, file object, or stream
  - Accepts strings, text/binary file objects, StringIO, or BytesIO
  - Yields LogEvent objects for each parsed event

- `parse_event(payload: str) -> LogEvent | None`
  - Parse a single log event from a string (convenience method)
  - Wraps `parse()` and returns the first event
  - Returns LogEvent or None if no event found

### LogEvent

Represents a parsed log event with extracted variables.

#### Methods

- `get_log_message() -> str`
  - Get the original log message

- `get_log_type() -> str`
  - Get the generated log type (template) with logical group names

- `get_capture_group(logical_capture_group_name: str, raw_output: bool = False) -> str | list | None`
  - Get the value of a capture group by its logical name
  - If `raw_output=False` (default), single values are unwrapped from lists
  - Returns None if capture group not found

- `get_capture_group_str_representation(field: str, raw_output: bool = False) -> str`
  - Get the string representation of a capture group value

- `get_resolved_dict() -> dict[str, str | list]`
  - Get a dictionary with all capture groups using logical (user-defined) names
  - Physical names (CGPrefix*) are converted to logical names
  - Timestamp fields are consolidated under "timestamp" key
  - Single-value lists are unwrapped to scalar values
  - "@LogType" is excluded from the output

- `__getitem__(key: str) -> str | list`
  - Access capture group values by name (e.g., `event['field_name']`)
  - Shorthand for `get_capture_group(key, raw_output=False)`

- `__str__() -> str`
  - Get formatted JSON representation of the log event with logical group names
  - Uses `get_resolved_dict()` internally

### Query

Query builder for parsing log events into structured data formats.

#### Constructor

- `Query(parser: Parser)`
  - Initialize a query with a configured parser

#### Methods

- `select(fields: list[str]) -> Query`
  - Select fields to extract from log events
  - Supports variable names, `"*"` for all variables, `"@log_type"` for log type, and `"@log_message"` for original message
  - The `"*"` wildcard can be combined with other fields (e.g., `["@log_type", "*"]`)
  - Returns self for method chaining

- `filter(predicate: Callable[[LogEvent], bool]) -> Query`
  - Filter log events using a predicate function
  - Predicate receives a LogEvent and returns True to include it, False to exclude
  - Returns self for method chaining
  - Example: `query.filter(lambda event: int(event['value']) > 50)`

- `from_(input: str | TextIO | BinaryIO | io.StringIO | io.BytesIO) -> Query`
  - Set the input source to parse
  - Accepts strings, text/binary file objects, StringIO, or BytesIO
  - Strings are automatically wrapped in StringIO
  - Returns self for method chaining

- `select_from(input: str | TextIO | BinaryIO | io.StringIO | io.BytesIO) -> Query`
  - Alias for `from_()`
  - Returns self for method chaining

- `from_stream(stream: io.StringIO | io.BytesIO) -> Query`
  - Set the input stream to parse (legacy method)
  - Consider using `from_()` for more flexible input handling
  - Returns self for method chaining

- `validate_query() -> Query`
  - Validate that the query is properly configured
  - Returns self for method chaining

- `to_dataframe() -> pd.DataFrame`
  - Convert parsed events to a pandas DataFrame
  - Requires pandas (install with `pip install log-surgeon-ffi[dataframe]`)

- `to_df() -> pd.DataFrame`
  - Alias for `to_dataframe()`

- `to_arrow() -> pa.Table`
  - Convert parsed events to a PyArrow Table
  - Requires pyarrow (install with `pip install log-surgeon-ffi[dataframe]`)

- `to_pa() -> pa.Table`
  - Alias for `to_arrow()`

- `get_rows() -> list[list]`
  - Extract rows of field values from parsed events

### SchemaCompiler

Compiler for constructing log-surgeon schema definitions.

#### Constructor

- `SchemaCompiler(delimiters: str = DEFAULT_DELIMITERS)`
  - Initialize a schema compiler with optional custom delimiters

#### Methods

- `add_var(name: str, regex: str, hide_var_name_if_named_group_present: bool = True) -> SchemaCompiler`
  - Add a variable pattern to the schema
  - Returns self for method chaining

- `add_timestamp(name: str, regex: str) -> SchemaCompiler`
  - Add a timestamp pattern to the schema
  - Returns self for method chaining

- `remove_var(var_name: str) -> SchemaCompiler`
  - Remove a variable from the schema
  - Returns self for method chaining

- `get_var(var_name: str) -> Variable`
  - Get a variable by name

- `compile() -> str`
  - Compile the final schema string

- `get_capture_group_name_resolver() -> GroupNameResolver`
  - Get the resolver for mapping logical to physical capture group names

### GroupNameResolver

Bidirectional mapping between logical (user-defined) and physical (auto-generated) group names.

#### Constructor

- `GroupNameResolver(physical_name_prefix: str)`
  - Initialize with a prefix for auto-generated physical names

#### Methods

- `create_new_physical_name(logical_name: str) -> str`
  - Create a new unique physical name for a logical name
  - Each call generates a new physical name

- `get_physical_names(logical_name: str) -> set[str]`
  - Get all physical names associated with a logical name

- `get_logical_name(physical_name: str) -> str`
  - Get the logical name for a physical name

### Pattern

Collection of common regex patterns for log parsing.

#### Class Attributes

- `Pattern.UUID`
  - Pattern for UUID (Universally Unique Identifier) strings

- `Pattern.IP_OCTET`
  - Pattern for a single IPv4 octet (0-255)

- `Pattern.IPV4`
  - Pattern for IPv4 addresses

- `Pattern.INT`
  - Pattern for integer numbers (with optional negative sign)

- `Pattern.FLOAT`
  - Pattern for floating-point numbers (with optional negative sign)

#### Example Usage

```python
from log_surgeon import Parser, Pattern

parser = Parser()
parser.add_var("ip", rf"IP: (?<ip_address>{Pattern.IPV4})")
parser.add_var("id", rf"ID: (?<uuid>{Pattern.UUID})")
parser.add_var("value", rf"value=(?<val>{Pattern.FLOAT})")
parser.compile()
```

## Key Concepts

### Delimiters

Delimiters are characters used to split log messages into tokens. The default delimiters include:
- Whitespace: space, tab (`\t`), newline (`\n`), carriage return (`\r`)
- Punctuation: `:`, `,`, `!`, `;`, `%`, `@`, `/`, `(`, `)`, `[`, `]`

You can customize delimiters when creating a Parser:

```python
parser = Parser(delimiters=r" \t\n,:")  # Custom delimiters
```

### Named Capture Groups

Use named capture groups in regex patterns to extract specific fields:

```python
parser.add_var("metric", r"metric=(?<metric_name>\w+) value=(?<value>\d+)")
```

The syntax `(?<name>pattern)` creates a capture group that can be accessed as `event['name']`.

### Using Raw F-Strings for Regex Patterns

**Best Practice:** Use raw f-strings (`rf"..."`) when specifying regex patterns to avoid escaping issues.

Raw f-strings combine the benefits of:
- **Raw strings (`r"..."`)**: No need to double-escape regex special characters like `\d`, `\w`, `\n`
- **F-strings (`f"..."`)**: Easy interpolation of variables and pattern constants

#### Why Use Raw F-Strings?

```python
# ❌ Without raw strings - requires double-escaping
parser.add_var("metric", "value=(\\d+)")  # Hard to read, error-prone

# ✅ With raw f-strings - single escaping, clean and readable
parser.add_var("metric", rf"value=(?<value>\d+)")
```

#### Watch Out for Braces

When using f-strings, literal `{` and `}` characters must be escaped by doubling them:

```python
from log_surgeon import Parser, Pattern

parser = Parser()

# ✅ Correct: Escape literal braces in regex
parser.add_var("json", rf"data={{(?<content>[^}}]+)}}")  # Matches: data={...}
parser.add_var("range", rf"range={{(?<min>\d+),(?<max>\d+)}}")  # Matches: range={10,20}

# ✅ Using Pattern constants with interpolation
parser.add_var("ip", rf"IP: (?<ip>{Pattern.IPV4})")
parser.add_var("float", rf"value=(?<val>{Pattern.FLOAT})")

# ✅ Common regex patterns
parser.add_var("digits", rf"\d+ items")  # No double-escaping needed
parser.add_var("word", rf"name=(?<name>\w+)")
parser.add_var("whitespace", rf"split\s+by\s+spaces")

parser.compile()
```

#### Examples: Raw F-Strings vs Regular Strings

```python
# Regular string - requires double-escaping
parser.add_var("path", "path=(?<path>\\w+/\\w+)")  # Hard to read

# Raw f-string - natural regex syntax
parser.add_var("path", rf"path=(?<path>\w+/\w+)")  # Clean and readable

# With interpolation
log_level = "INFO|WARN|ERROR"
parser.add_var("level", rf"(?<level>{log_level})")  # Easy to compose
```

**Recommendation:** Consistently use `rf"..."` for all regex patterns. This approach:
- Avoids double-escaping mistakes
- Makes patterns more readable
- Allows easy use of Pattern constants and variables
- Only requires watching for literal `{` and `}` characters (escape as `{{` and `}}`)

### Logical vs Physical Names

Internally, log-surgeon uses "physical" names (e.g., `CGPrefix0`, `CGPrefix1`) for capture groups, while you work with "logical" names (e.g., `user_id`, `thread`). The `GroupNameResolver` handles this mapping automatically.

### Schema Format

The schema defines delimiters, timestamps, and variables for parsing:

```
// schema delimiters
delimiters: \t\r\n:,!;%@/\(\)\[\]

// schema timestamps
timestamp:<timestamp_regex>

// schema variables
variable_name:<variable_regex>
```

When using the fluent API (`Parser.add_var()` and `Parser.compile()`), the schema is built automatically.

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
- C++20 compatible compiler

## License

Apache License 2.0 - See [LICENSE](LICENSE) for details.

## Links

- [Homepage](https://github.com/y-scope/log-surgeon-ffi-py)
- [Bug Tracker](https://github.com/y-scope/log-surgeon-ffi-py/issues)
- [log-surgeon C++ library](https://github.com/y-scope/log-surgeon)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
