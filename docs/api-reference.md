# API Reference

## Quick Reference

| Task                | Syntax                                       |
|---------------------|----------------------------------------------|
| Named capture       | `(?<name>pattern)`                           |
| Alternation         | `(?<name>opt1\|opt2)` or `(opt1)\|(opt2)`    |
| Optional (0 or 1)   | `?` or `{0,1}`                               |
| Match across delimiters | Use `[a-z ]*` (NOT `.*`)                 |
| Pattern string      | `rf"..."` (raw f-string recommended)         |
| Log type            | `.select(["@log_type"])`                     |
| Original message    | `.select(["@log_message"])`                  |

## Parser

High-level parser for extracting structured data from unstructured log messages.

### Constructor

- `Parser(delimiters: str = r" \t\r\n:,!;%@/()[]")`
  - Initialize a parser with optional custom delimiters
  - Default delimiters include space, tab, newline, and common punctuation
  - Note: Special characters no longer need to be escaped (as of log-surgeon 0.7.0)

### Methods

- `add_var(name: str, regex: str, priority: int = 0) -> Parser`
  - Add a variable pattern to the parser's schema
  - Supports named capture groups using `(?<name>)` syntax
  - `priority`: Controls ordering in schema (higher values appear first, default is 0)
    - Use negative values for generic patterns (e.g., -1, -2, etc. where more negative = lower priority)
    - Variables with same priority maintain insertion order
  - Use raw f-strings (`rf"..."`) for regex patterns (see [Key Concepts](key-concepts.md#using-raw-f-strings-for-regex-patterns))
  - Returns self for method chaining

- `add_timestamp(name: str, regex: str) -> Parser`
  - Add a timestamp pattern to the parser's schema
  - Returns self for method chaining

- `compile(enable_debug_logs: bool = False) -> None`
  - Build and initialize the parser with the configured schema
  - Must be called after adding variables and before parsing
  - Set `enable_debug_logs=True` to output debug information to stderr

- `parse(input: str | TextIO | BinaryIO | io.StringIO | io.BytesIO) -> Generator[LogEvent, None, None]`
  - Parse all log events from a string, file object, or stream
  - Accepts strings, text/binary file objects, StringIO, or BytesIO
  - Yields LogEvent objects for each parsed event

- `parse_event(payload: str) -> LogEvent | None`
  - Parse a single log event from a string (convenience method)
  - Wraps `parse()` and returns the first event
  - Returns LogEvent or None if no event found

## LogEvent

Represents a parsed log event with extracted variables.

### Methods

- `get_log_message() -> str`
  - Get the original log message

- `get_log_type() -> str`
  - Get the generated log type (template)

- `get_capture_group(name: str, raw_output: bool = False) -> str | list | None`
  - Get the value of a capture group by name
  - If `raw_output=False` (default), single values are unwrapped from lists
  - Returns None if capture group not found

- `get_capture_group_str_representation(field: str, raw_output: bool = False) -> str`
  - Get the string representation of a capture group value

- `get_resolved_dict() -> dict[str, str | list]`
  - Get a dictionary with all capture groups
  - Timestamp fields are consolidated under "timestamp" key
  - Single-value lists are unwrapped to scalar values
  - "@LogType" is excluded from the output

- `__getitem__(key: str) -> str | list`
  - Access capture group values by name (e.g., `event['field_name']`)
  - Shorthand for `get_capture_group(key, raw_output=False)`

- `__str__() -> str`
  - Get formatted JSON representation of the log event
  - Uses `get_resolved_dict()` internally

## Query

Query builder for parsing log events into structured data formats.

### Constructor

- `Query(parser: Parser)`
  - Initialize a query with a configured parser

### Methods

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

- `validate_query() -> Query`
  - Validate that the query is properly configured
  - Returns self for method chaining

- `to_dataframe() -> pd.DataFrame`
  - Convert parsed events to a pandas DataFrame

- `to_df() -> pd.DataFrame`
  - Alias for `to_dataframe()`

- `to_arrow() -> pa.Table`
  - Convert parsed events to a PyArrow Table

- `to_pa() -> pa.Table`
  - Alias for `to_arrow()`

- `get_rows() -> list[list]`
  - Extract rows of field values from parsed events

- `get_vars() -> set[str]`
  - Get all variable names (capture group names) defined in the schema

- `get_log_types() -> Generator[str, None, None]`
  - Get all unique log types from parsed events
  - Yields log types in the order they are first encountered
  - Useful for discovering log patterns in your data

- `get_log_type_counts() -> dict[str, int]`
  - Get count of occurrences for each unique log type
  - Returns dictionary mapping log types to their counts
  - Useful for analyzing log type distribution

- `get_log_type_with_sample(sample_size: int = 3) -> dict[str, list[str]]`
  - Get sample log messages for each unique log type
  - Returns dictionary mapping log types to lists of sample messages
  - Useful for understanding what actual messages match each template

## JsonParser

Parser for JSON-formatted logs that extracts variables from string fields and merges them back into the original JSON.

> **Note:** Extraction only works on string-type fields. Non-string fields (numbers, booleans, objects, arrays) are skipped during extraction.

### Constructor

- `JsonParser(parser: Parser)`
  - Initialize with a configured and compiled Parser instance
  - The Parser defines the extraction patterns to apply to JSON fields
  - By default, extracts from all string fields (equivalent to `target_fields("*")`)

### Methods

- `target_fields(fields: list[str] | str) -> JsonParser`
  - Configure which JSON fields to parse
  - By default (if not called), extracts from all string fields
  - Accepts flexible input:
    - Single field: `"message"` or `["message"]`
    - Multiple fields: `["message", "context.detail"]`
    - All fields: `"*"` or `["*"]`
  - Supports dot-notation for nested fields (e.g., `"context.message"`)
  - Returns self for method chaining

- `on_conflict(strategy: ConflictStrategy, prefix: str = "extracted.", key: str = "extracted") -> JsonParser`
  - Configure how to handle key conflicts when extracted names match existing JSON keys
  - Strategies: `NEST` (default), `PREFIX`, `OVERWRITE`, `RAISE`
  - Returns self for method chaining

- `include_log_type(include: bool = True) -> JsonParser`
  - Include the generated log type template in output under `@log_type`
  - Returns self for method chaining

- `parse(source: str | TextIO | BinaryIO | io.StringIO | io.BytesIO) -> Generator[dict, None, None]`
  - Parse JSON logs from an input source
  - Auto-detects NDJSON vs JSON array format
  - Yields enriched dictionaries with extracted variables

- `parse_one(json_line: str) -> dict`
  - Parse a single JSON line
  - Returns enriched dictionary

## ConflictStrategy

Enum for handling conflicts when extracted variable names match existing JSON keys.

| Strategy | Behavior |
|----------|----------|
| `NEST` | Put all extracted vars under a key (default, safest) |
| `PREFIX` | Add prefix to extracted variable names |
| `OVERWRITE` | Replace existing key (prints warning) |
| `RAISE` | Raise KeyError on conflict |

**NEST key conflict handling:** If the nest key (e.g., `"extracted"`) already exists in the JSON, the original value is preserved under `"original_value"` within the nested object. If an extracted variable is also named `"original_value"`, a warning is printed and the original JSON value takes precedence.

Example:
```python
from log_surgeon import ConflictStrategy, JsonParser

# NEST (default): {"message": "...", "extracted": {"user_id": "123"}}
json_parser.on_conflict(ConflictStrategy.NEST, key="extracted")

# If "extracted" already exists in JSON:
# Input:  {"message": "user=123", "extracted": "old_data"}
# Output: {"message": "...", "extracted": {"user_id": "123", "original_value": "old_data"}}

# PREFIX: {"message": "...", "parsed_user_id": "123"}
json_parser.on_conflict(ConflictStrategy.PREFIX, prefix="parsed_")

# OVERWRITE: {"message": "...", "user_id": "123"} (replaces existing)
json_parser.on_conflict(ConflictStrategy.OVERWRITE)

# RAISE: Raises KeyError if conflict detected
json_parser.on_conflict(ConflictStrategy.RAISE)
```

## SchemaCompiler

Compiler for constructing log-surgeon schema definitions.

### Constructor

- `SchemaCompiler(delimiters: str = DEFAULT_DELIMITERS)`
  - Initialize a schema compiler with optional custom delimiters

### Methods

- `add_var(name: str, regex: str, priority: int = 0) -> SchemaCompiler`
  - Add a variable pattern to the schema
  - `priority`: Controls ordering in schema (higher values appear first, default is 0)
    - Use negative values for generic patterns (e.g., -1, -2, etc. where more negative = lower priority)
    - Variables with same priority maintain insertion order
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

## PATTERN

Collection of pre-built regex patterns optimized for log parsing. These patterns follow log-surgeon's syntax requirements and are ready to use with named capture groups.

### Network Patterns

| Pattern | Description | Example Match |
|---------|-------------|---------------|
| `PATTERN.UUID` | UUID (Universally Unique Identifier) | `550e8400-e29b-41d4-a716-446655440000` |
| `PATTERN.IP_OCTET` | Single IPv4 octet (0-255) | `192`, `10`, `255` |
| `PATTERN.IPV4` | IPv4 address | `192.168.1.1`, `10.0.0.1` |
| `PATTERN.PORT` | Network port number (1-5 digits) | `80`, `8080`, `65535` |

### Numeric Patterns

| Pattern | Description | Example Match |
|---------|-------------|---------------|
| `PATTERN.INT` | Integer with optional negative sign | `42`, `-123`, `0` |
| `PATTERN.FLOAT` | Float with optional negative sign | `3.14`, `-123.456`, `0.5` |

### File System Patterns

| Pattern | Description | Example Match |
|---------|-------------|---------------|
| `PATTERN.LINUX_FILE_NAME_CHARSET` | Character set for Linux file names | `a-zA-Z0-9 ._-` |
| `PATTERN.LINUX_FILE_NAME` | Linux file name | `app.log`, `config-2024.yaml` |
| `PATTERN.LINUX_FILE_PATH` | Linux file path (relative) | `logs/app.log`, `var/log/system.log` |

### Character Sets and Word Patterns

| Pattern | Description | Example Match |
|---------|-------------|---------------|
| `PATTERN.JAVA_IDENTIFIER_CHARSET` | Java identifier character set | `a-zA-Z0-9_` |
| `PATTERN.JAVA_IDENTIFIER` | Java identifier | `myVariable`, `$value`, `Test123` |
| `PATTERN.LOG_LINE_CHARSET` | Common log line characters | Alphanumeric + symbols + whitespace |
| `PATTERN.LOG_LINE` | General log line content | `Error: connection timeout` |
| `PATTERN.LOG_LINE_NO_WHITE_SPACE_CHARSET` | Log line chars without whitespace | Alphanumeric + symbols only |
| `PATTERN.LOG_LINE_NO_WHITE_SPACE` | Log content without spaces | `ERROR`, `/var/log/app.log` |

### Java-Specific Patterns

| Pattern | Description | Example Match |
|---------|-------------|---------------|
| `PATTERN.JAVA_LITERAL_CHARSET` | Java literal character set | `a-zA-Z0-9_$` |
| `PATTERN.JAVA_PACKAGE_SEGMENT` | Single Java package segment | `com.`, `example.` |
| `PATTERN.JAVA_CLASS_NAME` | Java class name | `MyClass`, `ArrayList` |
| `PATTERN.JAVA_FULLY_QUALIFIED_CLASS_NAME` | Fully qualified class name | `java.util.ArrayList` |
| `PATTERN.JAVA_LOGGING_CODE_LOCATION_HINT` | Java logging location hint | `~[MyClass.java:42?]` |
| `PATTERN.JAVA_STACK_LOCATION` | Java stack trace location | `java.util.ArrayList.add(ArrayList.java:123)` |

### Example usage

```python
from log_surgeon import Parser, PATTERN

parser = Parser()

# Network patterns
parser.add_var("network", rf"IP: (?<ip>{PATTERN.IPV4}) Port: (?<port>{PATTERN.PORT})")

# Numeric patterns
parser.add_var("metrics", rf"value=(?<value>{PATTERN.FLOAT}) count=(?<count>{PATTERN.INT})")

# File system patterns
parser.add_var("file", rf"Opening (?<filepath>{PATTERN.LINUX_FILE_PATH})")

# Java patterns
parser.add_var("exception", rf"at (?<stack>{PATTERN.JAVA_STACK_LOCATION})")

parser.compile()
```

### Composing Patterns

PATTERN constants can be composed to build more complex patterns:

```python
from log_surgeon import Parser, PATTERN

parser = Parser()

# Combine multiple patterns
parser.add_var(
    "server_info",
    rf"Server (?<name>{PATTERN.JAVA_IDENTIFIER}) at (?<ip>{PATTERN.IPV4}):(?<port>{PATTERN.PORT})"
)

# Use character sets to build custom patterns
parser.add_var(
    "custom_id",
    rf"ID-(?<id>[{PATTERN.JAVA_IDENTIFIER_CHARSET}]+)"
)

parser.compile()
```
