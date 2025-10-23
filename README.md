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

**Note:** pandas and pyarrow are included as dependencies for DataFrame/Arrow support.

---

> **⚠️ IMPORTANT: READ BEFORE USING**
>
> **log-surgeon uses token-based parsing and has different regex behavior than traditional engines.**
>
> **You MUST read the [Key Concepts](#key-concepts) section and understand it fully before writing patterns, or you will encounter unexpected behavior and pain.**
>
> Critical differences:
> - **Strongly recommended: use raw f-strings (`rf"..."`)** for regex patterns to avoid escaping issues
> - Forward slashes `/` must be escaped as `\/` (e.g., for paths like `/abc/def`)
> - `.*` only matches within a single token (not across delimiters)
> - `abc|def` requires grouping: use `(abc)|(def)` instead
> - Use `{0,1}` for optional patterns, NOT `?`
>
> **[→ Read Key Concepts Now](#key-concepts)**

---

## Quick Start

### Basic Parsing

```python
from log_surgeon import Parser, PATTERN

# Parse a sample log event
log_line = "16/05/04 04:24:58 INFO Registering worker with 1 core and 4.0 GiB ram\n"

# Create a parser and define extraction patterns
parser = Parser()
parser.add_var("resource", rf"(?<memory_gb>{PATTERN.FLOAT}) GiB ram")
parser.compile()

# Parse a single event
event = parser.parse_event(log_line)

# Access extracted data
print(f"Message: {event.get_log_message().strip()}")
print(f"LogType: {event.get_log_type().strip()}")
print(f"Parsed Logs: {event}")
```

**Output:**
```
Message: 16/05/04 04:24:58 INFO Registering worker with 1 core and 4.0 GiB ram
LogType: 16/05/04 04:24:58 INFO Registering worker with 1 core and <memory_gb> GiB ram
Parsed Logs: {
  "core": "1"
}
```

### Multiple Capture Groups

```python
from log_surgeon import Parser

parser = Parser()

# Extract platform information (level, thread, component)
parser.add_var(
  "platform",
  rf"(?<platform_level>(INFO)|(WARN)|(ERROR)) \[(?<platform_thread>.+)\] (?<platform_component>.+):"
)

# Extract application-specific metrics
parser.add_var(
  "memoryStore",
  rf"MemoryStore started with capacity (?<memory_store_capacity_GiB>\d+\.\d+) GiB"
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
parser.add_var("metric", rf"value=(?<value>\d+)")
parser.compile()

# Parse from string (automatically converted to StringIO)
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
  rf"metric=(?<metric_name>\w+) value=(?<value>\d+)"
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
parser.add_var("metric", rf"metric=(?<metric_name>\w+) value=(?<value>\d+)")
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
parser.add_var("metric", rf"value=(?<value>\d+)")
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

### Analyzing Log Types

Discover and analyze log patterns in your data using log type analysis methods:

```python
from log_surgeon import Parser, Query

parser = Parser()
parser.add_var("metric", rf"value=(?<value>\d+)")
parser.add_var("status", rf"status=(?<status>\w+)")
parser.compile()

log_data = """
2024-01-01 INFO: Processing value=42
2024-01-01 INFO: Processing value=100
2024-01-01 WARN: System status=degraded
2024-01-01 INFO: Processing value=7
2024-01-01 ERROR: System status=failed
"""

query = Query(parser).from_(log_data)

# Get all unique log types
print("Unique log types:")
for log_type in query.get_log_types():
  print(f"  {log_type}")

# Reset stream for next analysis
query.from_(log_data)

# Get log type occurrence counts
print("\nLog type counts:")
counts = query.get_log_type_counts()
for log_type, count in sorted(counts.items(), key=lambda x: -x[1]):
  print(f"  {count:3d}  {log_type}")

# Reset stream for next analysis
query.from_(log_data)

# Get sample messages for each log type
print("\nLog type samples:")
samples = query.get_log_type_with_sample(sample_size=2)
for log_type, messages in samples.items():
  print(f"  {log_type}")
  for msg in messages:
    print(f"    - {msg.strip()}")
```

**Output:**
```
Unique log types:
  <timestamp> INFO: Processing <metric>
  <timestamp> WARN: System <status>
  <timestamp> ERROR: System <status>

Log type counts:
    3  <timestamp> INFO: Processing <metric>
    1  <timestamp> WARN: System <status>
    1  <timestamp> ERROR: System <status>

Log type samples:
  <timestamp> INFO: Processing <metric>
    - 2024-01-01 INFO: Processing value=42
    - 2024-01-01 INFO: Processing value=100
  <timestamp> WARN: System <status>
    - 2024-01-01 WARN: System status=degraded
  <timestamp> ERROR: System <status>
    - 2024-01-01 ERROR: System status=failed
```

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
  - Use raw f-strings (`rf"..."`) for regex patterns (see [Using Raw F-Strings](#using-raw-f-strings-for-regex-patterns))
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

- `to_df() -> pd.DataFrame`
  - Alias for `to_dataframe()`

- `to_arrow() -> pa.Table`
  - Convert parsed events to a PyArrow Table

- `to_pa() -> pa.Table`
  - Alias for `to_arrow()`

- `get_rows() -> list[list]`
  - Extract rows of field values from parsed events

- `get_vars() -> KeysView[str]`
  - Get all variable names (logical capture group names) defined in the schema

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

- `get_all_logical_names() -> KeysView[str]`
  - Get all logical names that have been registered

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

> **⚠️ CRITICAL: You must understand these concepts to use log-surgeon correctly.**
>
> log-surgeon works **fundamentally differently** from traditional regex engines like Python's `re` module, PCRE, or JavaScript regex. Skipping this section will lead to patterns that don't work as expected.

### Token-Based Parsing and Delimiters

**CRITICAL:** log-surgeon uses **token-based** parsing, not character-based regex matching like traditional regex engines. This is the most important difference that affects how patterns work.

#### How Tokenization Works

Delimiters are characters used to split log messages into tokens. The default delimiters include:
- Whitespace: space, tab (`\t`), newline (`\n`), carriage return (`\r`)
- Punctuation: `:`, `,`, `!`, `;`, `%`, `@`, `/`, `(`, `)`, `[`, `]`

For example, with default delimiters, the log message:
```
"abc def ghi"
```
is tokenized into three tokens: `["abc", "def", "ghi"]`

You can customize delimiters when creating a Parser:

```python
parser = Parser(delimiters=r" \t\n,:")  # Custom delimiters
```

#### Token-Based Pattern Matching

**Critical:** Patterns like `.*` only match **within a single token**, not across multiple tokens or delimiters.

```python
from log_surgeon import Parser

parser = Parser()  # Default delimiters include space
parser.add_var("token", rf"(?<match>d.*)")
parser.compile()

# With "abc def ghi" tokenized as ["abc", "def", "ghi"]
event = parser.parse_event("abc def ghi")

# ✅ Matches only "def" (single token starting with 'd')
# ❌ Does NOT match "def ghi" (would cross token boundary)
print(event['match'])  # Output: "def"
```

**In a traditional regex engine**, `d.*` would match `"def ghi"` (everything from 'd' to end).
**In log-surgeon**, `d.*` matches only `"def"` because patterns cannot cross delimiter boundaries.

#### Why Token-Based?

Token-based parsing enables:
- **Faster parsing** by reducing search space
- **Predictable behavior** aligned with log structure
- **Efficient log type generation** for analytics

#### Working with Token Boundaries

To match across multiple tokens, you must use **character classes** like `[a-zA-Z]*` instead of `.`:

```python
from log_surgeon import Parser

parser = Parser()  # Default delimiters include space

# ❌ Using .* - only matches within a single token
parser.add_var("wrong", rf"(?<match>d.*)")  # Matches only "def"

# ✅ Using character classes - matches across tokens
parser.add_var("correct", rf"(?<match>d[a-z ]*i)")  # Matches "def ghi"
parser.compile()

event = parser.parse_event("abc def ghi")
print(event['match'])  # Output: "def ghi"
```

**Key Rule:** Character classes like `[a-zA-Z]*`, `[a-z ]*`, or `[\w\s]*` can match across token boundaries, but `.*` cannot.

#### Alternation Requires Grouping

**CRITICAL:** Alternation (`|`) works differently in log-surgeon compared to traditional regex engines. You **must** use parentheses to group alternatives.

```python
from log_surgeon import Parser

parser = Parser()

# ❌ WRONG: Without grouping - matches "ab" AND ("c" OR "d") AND "ef"
parser.add_var("wrong", rf"(?<word>abc|def)")
# In log-surgeon, this is interpreted as: "ab" + "c|d" + "ef"
# Matches: "abcef" or "abdef" (NOT "abc" or "def")

# ✅ CORRECT: With grouping - matches "abc" OR "def"
parser.add_var("correct", rf"(?<word>(abc)|(def))")
# Matches: "abc" or "def"
parser.compile()
```

**In traditional regex engines**, `abc|def` means "abc" OR "def".
**In log-surgeon**, `abc|def` means "ab" + ("c" OR "d") + "ef".

**Key Rule:** Always use `(abc)|(def)` syntax for alternation to match complete alternatives.

```python
# More examples:
parser.add_var("level", rf"(?<level>(ERROR)|(WARN)|(INFO))")  # ✅ Correct
parser.add_var("status", rf"(?<status>(success)|(failure))")  # ✅ Correct
parser.add_var("bad", rf"(?<status>success|failure)")         # ❌ Wrong - unexpected behavior
```

#### Optional Patterns

For optional patterns, use `{0,1}` instead of `*`:

```python
from log_surgeon import Parser

parser = Parser()

# ❌ Avoid using * for optional patterns (matches 0 or more)
parser.add_var("avoid", rf"(?<level>(ERROR)|(WARN))*")  # Can match empty string or multiple repetitions

# ❌ Do not use ? for optional patterns
parser.add_var("avoid2", rf"(?<level>(ERROR)|(WARN))?")  # May not work as expected

# ✅ Use {0,1} for optional patterns (matches 0 or 1)
parser.add_var("optional", rf"(?<level>(ERROR)|(WARN)){0,1}")  # Matches 0 or 1 occurrence
parser.compile()
```

**Best Practice:** Use `{0,1}` for optional elements. Avoid `*` (0 or more) and `?` for optional matching.

You can also explicitly include delimiters in your pattern:

```python
# To match "def ghi", explicitly include the space delimiter
parser.add_var("multi", rf"(?<match>d\w+\s+\w+)")
# This matches "def " as one token segment, followed by "ghi"
```

Or adjust your delimiters to change tokenization behavior:

```python
# Use only newline as delimiter to treat entire lines as tokens
parser = Parser(delimiters=r"\n")
```

### Named Capture Groups

Use named capture groups in regex patterns to extract specific fields:

```python
parser.add_var("metric", rf"metric=(?<metric_name>\w+) value=(?<value>\d+)")
```

The syntax `(?<name>pattern)` creates a capture group that can be accessed as `event['name']`.

**Note:** See [Using Raw F-Strings](#using-raw-f-strings-for-regex-patterns) for best practices on writing regex patterns.

### Using Raw F-Strings for Regex Patterns

> **⚠️ STRONGLY RECOMMENDED: Use raw f-strings (`rf"..."`) for all regex patterns.**
>
> While not absolutely required, using regular strings will likely cause escaping issues and pattern failures. Raw f-strings prevent these problems.

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

#### Watch Out for Braces in F-Strings

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
- Avoids double-escaping mistakes that break patterns
- Makes patterns more readable
- Allows easy use of Pattern constants and variables
- Only requires watching for literal braces `{` and `}` in f-strings (escape as `{{` and `}}`)

Using regular strings (`"..."`) will require double-escaping (e.g., `"\\d+"`) which is error-prone and hard to read.

### Forward Slash Escaping

**CRITICAL:** In log-surgeon, forward slashes `/` **must always be escaped** as `\/`. This is a log-surgeon-specific requirement.

```python
from log_surgeon import Parser

parser = Parser()

# ✅ Correct: Escape forward slashes
parser.add_var("path", rf"(?<path>\/[a-z]+\/[a-z]+)")  # Matches: /abc/def
parser.add_var("url", rf"(?<url>https:\/\/[a-z.]+)")   # Matches: https://example.com

# ❌ Wrong: Unescaped forward slashes
parser.add_var("wrong", rf"(?<path>/[a-z]+/[a-z]+)")   # Will not work correctly

parser.compile()
```

**In traditional regex engines** (Python `re`, PCRE, etc.), `/` does not need escaping (except in JavaScript regex literals).
**In log-surgeon**, `/` **must always be escaped** as `\/` due to log-surgeon's internal design.

This is especially important when matching:
- File paths: `/var/log/app.log` → `\/var\/log\/app\.log`
- URLs: `https://example.com/api` → `https:\/\/example\.com\/api`
- Date formats: `2024/01/15` → `2024\/01\/15`

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

# Install the project in editable mode
pip install -e .

# Build the extension
cmake -S . -B build
cmake --build build
```

### Running Tests

```bash
# Install test dependencies
pip install pytest

# Run tests
python -m pytest tests/
```

## Requirements

- Python >= 3.9
- pandas
- pyarrow

### Build Requirements

- C++20 compatible compiler
- CMake >= 3.15

## License

Apache License 2.0 - See [LICENSE](LICENSE) for details.

## Links

- [Homepage](https://github.com/y-scope/log-surgeon-ffi-py)
- [Bug Tracker](https://github.com/y-scope/log-surgeon-ffi-py/issues)
- [log-surgeon C++ library](https://github.com/y-scope/log-surgeon)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
