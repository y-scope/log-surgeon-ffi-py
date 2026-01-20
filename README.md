# log-surgeon-ffi

`log-surgeon-ffi` provides Python foreign function interface (FFI) bindings for
[`log-surgeon`](https://github.com/y-scope/log-surgeon).

---

## Quick navigation

[**Overview**](#overview)
* [Why `log-surgeon`?](#why-log-surgeon)
* [Key capabilities](#key-capabilities)
* [Structured output and downstream capabilities](#structured-output-and-downstream-capabilities)
* [When to use `log-surgeon`](#when-to-use-log-surgeon)

[**Getting started**](#getting-started)
* [System requirements](#system-requirements)
* [Installation](#installation)
* [First steps](#first-steps)
* [Important prerequisites](#important-prerequisites)
* [Quick start examples](#quick-start-examples)

[**Key concepts**](#key-concepts)
* [Token-based parsing and delimiters](#token-based-parsing-and-delimiters)
* [Named capture groups](#named-capture-groups)
* [Variable priority and ordering](#variable-priority-and-ordering)
* [Using raw f-strings for regex patterns](#using-raw-f-strings-for-regex-patterns)

[**Reference**](#reference)
* [Parser API](#parser)
* [Query API](#query)
* [JsonParser API](#jsonparser)
* [ConflictStrategy](#conflictstrategy)
* [PATTERN constants](#pattern)

[**Development**](#development)
* [Building from source](#building-from-source)
* [Running tests](#running-tests)

---

## Overview

[`log-surgeon`](https://github.com/y-scope/log-surgeon), is a high-performance C++ library that
enables efficient extraction of structured information from unstructured log files.

### Why `log-surgeon`?

Traditional regex engines are often slow to execute, prone to errors, and costly to maintain.

`log-surgeon` streamlines the process by identifying, extracting, and labeling variable values with
semantic context, and then inferring a log template in a single pass. `log-surgeon` is also built to
accommodate structural variability. Values may shift position, appear multiple times, or change order
entirely, but with `log-surgeon`, you simply define the variable patterns, and `log-surgeon`
JIT-compiles a tagged-DFA state machine to drive the full pipeline.

### Key capabilities

* **Extract variables** from log messages using regex patterns with named capture groups
* **Generate log types** (templates) automatically for log analysis
* **Parse streams** efficiently for large-scale log processing
* **Export data** to pandas DataFrames and PyArrow Tables

### Structured output and downstream capabilities

Unstructured log data is automatically transformed into structured semantic representations.

* **Log types (templates)**: Variables are replaced with placeholders to form reusable templates.
  For example, roughly 200,000 Spark log messages can reduce to about 55 distinct templates, which
  supports pattern analysis and anomaly detection.

* **Semantic Variables**: Extracted key-value pairs with semantic context (e.g., `app_id`,
  `app_name`, `worker_id`) can be used directly for analysis.

This structured output unlocks powerful downstream capabilities:

* **Knowledge graph construction.** Build relationship graphs between entities extracted from logs
  (e.g., linking `app_id` → `app_name` → `worker_id`).

* **Template-based summarization.** Compress massive datasets into compact template sets for human
  and agent consumption. Templates act as natural tokens for LLMs. Instead of millions of raw lines,
  provide a small number of distinct templates with statistics.

* **Hybrid search** Combine free-text search with structured queries. Log types enable
  auto-completion and query suggestions on large datasets. Instead of searching through millions of
  raw log lines, search across a compact set of templates first. Then project and filter on
  structured variables (e.g., `status == "ERROR"`, `response_time > 1000`), and aggregate for
  analysis.

* **Agentic automation.** Agents can query by template, analyze variable distributions, identify
  anomalies, and automate debugging tasks using structured signals rather than raw text.

### When to use `log-surgeon`

**Good fit**
* Large-scale log processing (millions of lines)
* Extracting structured data from semi-structured logs
* Generating log templates for analytics
* Multi-line log events (stack traces, JSON dumps)
* Performance-critical parsing

**Not ideal**
* Simple one-off text extraction (use Python `re` module)
* Highly irregular text without consistent delimiters
* Patterns requiring full PCRE features (lookahead, backreferences)

---

## Getting started

Follow the instructions below to get started with `log-surgeon-ffi`.

### System requirements

- Python >= 3.9
- pandas
- pyarrow

#### Build requirements

- C++20 compatible compiler
- CMake >= 3.15

### Installation

To install the library with pandas and PyArrow support for DataFrame/Arrow table exports, run the
following command:

```bash
pip install log-surgeon-ffi
```

To verify your installation, run the following command:

```bash
python -c "from log_surgeon import Parser; print('Installation successful.')"
```

**Note:** If you only need core parsing without DataFrame or Arrow exports, you can install a
minimal environment, although pandas and PyArrow are included by default for convenience.

### First steps

After installation, follow these steps:

1. **Read [Key Concepts](#key-concepts).** Token based parsing differs from traditional regex.
2. **Run a [Quick start example](#quick-start-examples)** to see how it works.
3. **Use `rf"..."` for patterns** to avoid escaping issues. See
   [Using Raw f-strings](#using-raw-f-strings-for-regex-patterns).
4. **Check out [examples/](examples/)** to study some complete working examples.

---

> ### Important prerequisites
> 
> `log-surgeon` uses token-based parsing, and its regex behavior differs from traditional engines.
> Read the [Key Concepts](#key-concepts) section before writing patterns.
> 
> Critical differences between token-based parsing and traditional regex behavior:
> 
> * `.*` only matches within a single token (not across delimiters)
> * Use `?` or `{0,1}` for optional patterns (0 or 1 occurrences)
> 
> **Tip:** Use raw f-strings (`rf"..."`) for regex patterns. See 
> [Using Raw f-strings](#using-raw-f-strings-for-regex-patterns) for more details.

---

### Quick start examples

Use the following examples to get started.

#### Basic parsing

The following code parses a simple log event with `log-surgeon`.

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
  "memory_gb": "4.0"
}
```

We can see that the parser extracted structured data from the unstructured log line:
* ***Message**: The original log line
* **LogType**: Template with variable placeholder `<memory_gb>` showing the pattern structure
* **Parsed variables**: Successfully extracted `memory_gb` value of "4.0" from the pattern match

#### Try it yourself

Copy this code and modify the pattern to extract both `memory_gb` AND `cores`:

```python
from log_surgeon import Parser, PATTERN

log_line = "16/05/04 04:24:58 INFO Registering worker with 1 core and 4.0 GiB ram\n"
parser = Parser()
# TODO: Add pattern to capture both "1" (cores) and "4.0" (memory_gb)
parser.add_var("resource", rf"...")
parser.compile()

event = parser.parse_event(log_line)
print(f"Cores: {event['cores']}, Memory: {event['memory_gb']}")
```

<details>
<summary>Solution</summary>

```python
parser.add_var("resource", rf"(?<cores>\d+) core and (?<memory_gb>{PATTERN.FLOAT}) GiB ram")
```
</details>

---

#### Using priority for pattern ordering

When you have both specific and generic patterns, use priority to ensure specific patterns match first:

```python
from log_surgeon import Parser, PATTERN

log_line = "value:123 pi:3.14159 temp:98.6"

parser = Parser()

# Generic fallback pattern (low priority)
parser.add_var("generic_num", rf"(?<num>\d+)", priority=-1)

# Specific pattern for floats (higher priority)
parser.add_var("float_val", rf"(?<float>{PATTERN.FLOAT})", priority=1)

parser.compile()
event = parser.parse_event(log_line)

print(f"Float: {event['float']}")     # 3.14159 (matched by float_val)
print(f"Num: {event['num']}")         # 123 (matched by generic_num)
# Note: 98.6 matched by float_val, not split by generic_num
```

**Without priority**, the generic `\d+` pattern added first could match "3" and "98" separately before the float pattern tries. **With priority**, the float pattern is tried first, ensuring correct extraction of decimal numbers.

---

#### Multiple capture groups

The following code parses a more-complex log event.

```python
from log_surgeon import Parser, PATTERN

# Parse a sample log event
log_line = """16/05/04 12:22:37 WARN server.TransportChannelHandler: Exception in connection from spark-35/192.168.10.50:55392
java.io.IOException: Connection reset by peer
        at sun.nio.ch.FileDispatcherImpl.read0(Native Method)
        at sun.nio.ch.SocketDispatcher.read(SocketDispatcher.java:39)
        at sun.nio.ch.IOUtil.readIntoNativeBuffer(IOUtil.java:223)
        at sun.nio.ch.IOUtil.read(IOUtil.java:192)
        at sun.nio.ch.SocketChannelImpl.read(SocketChannelImpl.java:380)
        at io.netty.buffer.PooledUnsafeDirectByteBuf.setBytes(PooledUnsafeDirectByteBuf.java:313)
        at io.netty.buffer.AbstractByteBuf.writeBytes(AbstractByteBuf.java:881)
        at io.netty.channel.socket.nio.NioSocketChannel.doReadBytes(NioSocketChannel.java:242)
        at io.netty.channel.nio.AbstractNioByteChannel$NioByteUnsafe.read(AbstractNioByteChannel.java:119)
        at io.netty.channel.nio.NioEventLoop.processSelectedKey(NioEventLoop.java:511)
        at io.netty.channel.nio.NioEventLoop.processSelectedKeysOptimized(NioEventLoop.java:468)
        at io.netty.channel.nio.NioEventLoop.processSelectedKeys(NioEventLoop.java:382)
        at io.netty.channel.nio.NioEventLoop.run(NioEventLoop.java:354)
        at io.netty.util.concurrent.SingleThreadEventExecutor$2.run(SingleThreadEventExecutor.java:111)
        at java.lang.Thread.run(Thread.java:750)
"""

# Create a parser and define extraction patterns
parser = Parser()

# Add timestamp pattern
parser.add_timestamp("TIMESTAMP_SPARK_1_6", rf"\d{{2}}/\d{{2}}/\d{{2}} \d{{2}}:\d{{2}}:\d{{2}}")

# Add variable patterns
parser.add_var("SYSTEM_LEVEL", rf"(?<level>INFO|WARN|ERROR)")
parser.add_var("SPARK_HOST_IP_PORT", rf"(?<spark_host>spark\-{PATTERN.INT})/(?<system_ip>{PATTERN.IPV4}):(?<system_port>{PATTERN.PORT})")
parser.add_var(
  "SYSTEM_EXCEPTION",
  rf"(?<system_exception_type>({PATTERN.JAVA_PACKAGE_SEGMENT})+[{PATTERN.JAVA_IDENTIFIER_CHARSET}]*Exception): "
  rf"(?<system_exception_msg>{PATTERN.LOG_LINE})"
)
parser.add_var(
  rf"SYSTEM_STACK_TRACE",
  rf"(\s{{1,4}}at (?<system_stack>{PATTERN.JAVA_STACK_LOCATION})"
)
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
Message: 16/05/04 12:22:37 WARN server.TransportChannelHandler: Exception in connection from spark-35/192.168.10.50:55392
java.io.IOException: Connection reset by peer
        at sun.nio.ch.FileDispatcherImpl.read0(Native Method)
        at sun.nio.ch.SocketDispatcher.read(SocketDispatcher.java:39)
        at sun.nio.ch.IOUtil.readIntoNativeBuffer(IOUtil.java:223)
        at sun.nio.ch.IOUtil.read(IOUtil.java:192)
        at sun.nio.ch.SocketChannelImpl.read(SocketChannelImpl.java:380)
        at io.netty.buffer.PooledUnsafeDirectByteBuf.setBytes(PooledUnsafeDirectByteBuf.java:313)
        at io.netty.buffer.AbstractByteBuf.writeBytes(AbstractByteBuf.java:881)
        at io.netty.channel.socket.nio.NioSocketChannel.doReadBytes(NioSocketChannel.java:242)
        at io.netty.channel.nio.AbstractNioByteChannel$NioByteUnsafe.read(AbstractNioByteChannel.java:119)
        at io.netty.channel.nio.NioEventLoop.processSelectedKey(NioEventLoop.java:511)
        at io.netty.channel.nio.NioEventLoop.processSelectedKeysOptimized(NioEventLoop.java:468)
        at io.netty.channel.nio.NioEventLoop.processSelectedKeys(NioEventLoop.java:382)
        at io.netty.channel.nio.NioEventLoop.run(NioEventLoop.java:354)
        at io.netty.util.concurrent.SingleThreadEventExecutor$2.run(SingleThreadEventExecutor.java:111)
        at java.lang.Thread.run(Thread.java:750)
LogType: <timestamp> <level> server.TransportChannelHandler: Exception in connection from <spark_host>/<system_ip>:<system_port>
<system_exception_type>: <system_exception_msg><newLine>        at <system_stack><newLine>        at <system_stack><newLine>        at <system_stack><newLine>        at <system_stack><newLine>        at <system_stack><newLine>        at <system_stack><newLine>        at <system_stack><newLine>        at <system_stack><newLine>        at <system_stack><newLine>        at <system_stack><newLine>        at <system_stack><newLine>        at <system_stack><newLine>        at <system_stack><newLine>        at <system_stack><newLine>        at <system_stack><newLine>
Parsed Logs: {
  "timestamp": "16/05/04 12:22:37",
  "level": "WARN",
  "spark_host": "spark-35",
  "system_ip": "192.168.10.50",
  "system_port": "55392",
  "system_exception_type": "java.io.IOException",
  "system_exception_msg": "Connection reset by peer",
  "system_stack": [
    "sun.nio.ch.FileDispatcherImpl.read0(Native Method)",
    "sun.nio.ch.SocketDispatcher.read(SocketDispatcher.java:39)",
    "sun.nio.ch.IOUtil.readIntoNativeBuffer(IOUtil.java:223)",
    "sun.nio.ch.IOUtil.read(IOUtil.java:192)",
    "sun.nio.ch.SocketChannelImpl.read(SocketChannelImpl.java:380)",
    "io.netty.buffer.PooledUnsafeDirectByteBuf.setBytes(PooledUnsafeDirectByteBuf.java:313)",
    "io.netty.buffer.AbstractByteBuf.writeBytes(AbstractByteBuf.java:881)",
    "io.netty.channel.socket.nio.NioSocketChannel.doReadBytes(NioSocketChannel.java:242)",
    "io.netty.channel.nio.AbstractNioByteChannel$NioByteUnsafe.read(AbstractNioByteChannel.java:119)",
    "io.netty.channel.nio.NioEventLoop.processSelectedKey(NioEventLoop.java:511)",
    "io.netty.channel.nio.NioEventLoop.processSelectedKeysOptimized(NioEventLoop.java:468)",
    "io.netty.channel.nio.NioEventLoop.processSelectedKeys(NioEventLoop.java:382)",
    "io.netty.channel.nio.NioEventLoop.run(NioEventLoop.java:354)",
    "io.netty.util.concurrent.SingleThreadEventExecutor$2.run(SingleThreadEventExecutor.java:111)",
    "java.lang.Thread.run(Thread.java:750)"
  ]
}
```

The parser extracted **multiple named capture groups** from a complex multi-line Java stack trace:
* **Scalar fields**: `timestamp`, `level`, `spark_host`, `system_ip`, `system_port`,
  `system_exception_type`, `system_exception_msg`
* **Array field**: `system_stack` contains all 15 stack trace locations (demonstrates automatic
  aggregation of repeated capture groups)
* **LogType**: Template shows the structure with `<newLine>` markers indicating line boundaries in
  the original log

---

#### Stream parsing

When parsing log streams or files, timestamps are **required** to perform contextual anchoring.
Timestamps act as delimiters that separate individual log events, enabling the parser to correctly
group multi-line entries (like stack traces) into single events.

```python
from log_surgeon import Parser, PATTERN

# Parse from string (automatically converted to io.StringIO)
SAMPLE_LOGS = """16/05/04 04:31:13 INFO master.Master: Registering app SparkSQL::192.168.10.76
16/05/04 12:32:37 WARN server.TransportChannelHandler: Exception in connection from spark-35/192.168.10.50:55392
java.io.IOException: Connection reset by peer
        at sun.nio.ch.FileDispatcherImpl.read0(Native Method)
        at sun.nio.ch.SocketDispatcher.read(SocketDispatcher.java:39)
        at sun.nio.ch.IOUtil.readIntoNativeBuffer(IOUtil.java:223)
        at sun.nio.ch.IOUtil.read(IOUtil.java:192)
        at sun.nio.ch.SocketChannelImpl.read(SocketChannelImpl.java:380)
        at io.netty.buffer.PooledUnsafeDirectByteBuf.setBytes(PooledUnsafeDirectByteBuf.java:313)
        at io.netty.buffer.AbstractByteBuf.writeBytes(AbstractByteBuf.java:881)
        at io.netty.channel.socket.nio.NioSocketChannel.doReadBytes(NioSocketChannel.java:242)
        at io.netty.channel.nio.AbstractNioByteChannel$NioByteUnsafe.read(AbstractNioByteChannel.java:119)
        at io.netty.channel.nio.NioEventLoop.processSelectedKey(NioEventLoop.java:511)
        at io.netty.channel.nio.NioEventLoop.processSelectedKeysOptimized(NioEventLoop.java:468)
        at io.netty.channel.nio.NioEventLoop.processSelectedKeys(NioEventLoop.java:382)
        at io.netty.channel.nio.NioEventLoop.run(NioEventLoop.java:354)
        at io.netty.util.concurrent.SingleThreadEventExecutor$2.run(SingleThreadEventExecutor.java:111)
        at java.lang.Thread.run(Thread.java:750)
16/05/04 04:37:53 INFO master.Master: 192.168.10.76:41747 got disassociated, removing it.
"""

# Define parser with patterns
parser = Parser()
# REQUIRED: Timestamp acts as contextual anchor to separate individual log events in the stream
parser.add_timestamp("TIMESTAMP_SPARK_1_6", rf"\d{{2}}/\d{{2}}/\d{{2}} \d{{2}}:\d{{2}}:\d{{2}}")
parser.add_var("SYSTEM_LEVEL", rf"(?<level>INFO|WARN|ERROR)")
parser.add_var("SPARK_APP_NAME", rf"(?<spark_app_name>SparkSQL::{PATTERN.IPV4})")
parser.add_var("SPARK_HOST_IP_PORT", rf"(?<spark_host>spark\-{PATTERN.INT})/(?<system_ip>{PATTERN.IPV4}):(?<system_port>{PATTERN.PORT})")
parser.add_var(
    "SYSTEM_EXCEPTION",
    rf"(?<system_exception_type>({PATTERN.JAVA_PACKAGE_SEGMENT})+[{PATTERN.JAVA_IDENTIFIER_CHARSET}]*Exception): "
    rf"(?<system_exception_msg>{PATTERN.LOG_LINE})"
)
parser.add_var(
    rf"SYSTEM_STACK_TRACE", rf"(\s{{1,4}}at (?<system_stack>{PATTERN.JAVA_STACK_LOCATION})"
)
parser.add_var("IP_PORT", rf"(?<system_ip>{PATTERN.IPV4}):(?<system_port>{PATTERN.PORT})")
parser.compile()

# Stream parsing: iterate over multi-line log events
for idx, event in enumerate(parser.parse(SAMPLE_LOGS)):
    print(f"log-event-{idx} log template type:{event.get_log_type().strip()}")
```

**Output:**
```
log-event-0 log template type:<timestamp> <level> master.Master: Registering app <spark_app_name>
log-event-1 log template type:<timestamp> <level> server.TransportChannelHandler: Exception in connection from <spark_host>/<system_ip>:<system_port>
<system_exception_type>: <system_exception_msg><newLine>        at <system_stack><newLine>        at <system_stack><newLine>        at <system_stack><newLine>        at <system_stack><newLine>        at <system_stack><newLine>        at <system_stack><newLine>        at <system_stack><newLine>        at <system_stack><newLine>        at <system_stack><newLine>        at <system_stack><newLine>        at <system_stack><newLine>        at <system_stack><newLine>        at <system_stack><newLine>        at <system_stack><newLine>        at <system_stack>
log-event-2 log template type:<timestamp> <level> master.Master: <system_ip>:<system_port> got disassociated, removing it.<newLine>
```

The parser successfully separated the log stream into **three distinct events** using timestamps as
contextual anchors:
* **Event 0**: Single-line app registration log
* **Event 1**: Multi-line exception with 15 stack trace lines (demonstrates how timestamps bind
  multi-line events together)
* **Event 2**: Single-line disassociation log

Each log type shows the template structure with variable placeholders (`<level>`, `<system_ip>`,
etc.), enabling pattern-based log analysis and grouping.

---

#### Using `PATTERN` constants

The `PATTERN` class provides pre-built regex patterns for common log elements like IP addresses,
UUIDs, numbers, and file paths. See the [PATTERN reference](#pattern) for the complete list of
available patterns.

```python
from log_surgeon import Parser, PATTERN

parser = Parser()
parser.add_var("network", rf"IP: (?<ip>{PATTERN.IPV4}) UUID: (?<id>{PATTERN.UUID})")
parser.add_var("metrics", rf"value=(?<value>{PATTERN.FLOAT})")
parser.compile()

log_line = "IP: 192.168.1.1 UUID: 550e8400-e29b-41d4-a716-446655440000 value=42.5"
event = parser.parse_event(log_line)

print(f"IP: {event['ip']}")
print(f"UUID: {event['id']}")
print(f"Value: {event['value']}")
```

**Output:**
```
IP: 192.168.1.1
UUID: 550e8400-e29b-41d4-a716-446655440000
Value: 42.5
```

---

#### Export to DataFrame

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

---

#### JSON log parsing

Parse JSON-formatted logs by extracting variables from string fields.

**Required steps:**
1. Create a `Parser` with extraction patterns using `add_var()`
2. Call `parser.compile()` (required before use)
3. Create a `JsonParser` wrapping the compiled `Parser`
4. Call `parse()` for multiple JSON objects or `parse_one()` for a single object

**Minimal complete example:**
```python
from log_surgeon import JsonParser, Parser

# Step 1: Create parser with extraction patterns
parser = Parser()
parser.add_var("user_info", rf"user=(?<user_id>\d+)")  # (?<name>...) = named capture group
parser.add_var("status", rf"status=(?<status>\w+)")

# Step 2: Compile (required!)
parser.compile()

# Step 3: Create JsonParser
json_parser = JsonParser(parser)

# Step 4: Parse JSON
result = json_parser.parse_one('{"message": "user=123 status=ok"}')
print(result)
# Output: {'message': 'user=123 status=ok', 'extracted': {'user_id': '123', 'status': 'ok'}}
```

**Default behavior - extracts from ALL string fields:**
```python
json_parser = JsonParser(parser)  # No target_fields() call

input_json = '{"field1": "user=100", "field2": "user=200", "count": 42}'
result = json_parser.parse_one(input_json)
# Output: {'field1': 'user=100', 'field2': 'user=200', 'count': 42,
#          'extracted': {'user_id': ['100', '200']}}
# Note: 'count' (number) is skipped, values from multiple fields are aggregated into a list
```

**Configure target fields:**
```python
# Default: all string fields (equivalent to "*")
json_parser = JsonParser(parser)
json_parser = JsonParser(parser).target_fields("*")  # Explicit "all strings"

# Limit to specific field(s)
json_parser = JsonParser(parser).target_fields("message")  # Single field
json_parser = JsonParser(parser).target_fields(["message", "context.detail"])  # Multiple fields

# Supports dot-notation for nested fields: "context.detail" accesses {"context": {"detail": "..."}}
```

**Parse multiple JSON objects (NDJSON or JSON array):**
```python
# NDJSON format (newline-delimited)
json_logs = """
{"ts": "2024-01-01", "message": "user=123 request"}
{"ts": "2024-01-02", "message": "user=456 status=failed"}
"""

for enriched in json_parser.parse(json_logs):
    print(enriched)

# Also accepts JSON array format: [{"message": "..."}, {"message": "..."}]
```

**Error handling:**
```python
import json

try:
    result = json_parser.parse_one('invalid json')
except json.JSONDecodeError as e:
    print(f"Invalid JSON: {e}")
```

**Key behaviors:**
- Extraction only works on string fields (numbers, booleans, objects, arrays are skipped)
- Multiple matches across fields are aggregated into lists
- Results are placed under `"extracted"` key by default (configurable via `on_conflict()`)
- Supports NDJSON (one object per line) and JSON array formats (auto-detected)

See [JsonParser API Reference](#jsonparser) for full configuration options, or run the complete example:
```bash
python examples/json_log_parsing.py
```

---

#### Filtering events

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

---

#### Including log template type and log message

Use special fields `@log_type` and `@log_message` to include alongside extracted variables:

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

---

#### Analyzing Log Types

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

---

## Key concepts

> **CRITICAL: You must understand these concepts to use `log-surgeon` correctly.**
>
> `log-surgeon` works **fundamentally differently** from traditional regex engines like Python's
> `re` module, PCRE, or JavaScript regex. Skipping this section may lead to patterns that don't
> work as expected.

### Token-based parsing and delimiters

**CRITICAL:** `log-surgeon` uses **token-based** parsing, not character-based regex matching like
traditional regex engines. This is the most important difference that affects how patterns work.

#### How tokenization works

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
parser = Parser(delimiters=r" \t\n,:")  # Custom delimiters (no escaping needed for special chars)
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

# Matches only "def" (single token starting with 'd')
# Does NOT match "def ghi" (would cross token boundary)
print(event['match'])  # Output: "def"
```

**In a traditional regex engine**, `d.*` would match `"def ghi"` (everything from 'd' to end).
**In log-surgeon**, `d.*` matches only `"def"` because patterns cannot cross delimiter boundaries.

#### Why token-based?

Token-based parsing enables:
- **Faster parsing** by reducing search space
- **Predictable behavior** aligned with log structure
- **Efficient log type generation** for analytics

#### Working with token boundaries

To match across multiple tokens, you must use **character classes** like `[a-zA-Z]*` instead of `.`:

```python
from log_surgeon import Parser

parser = Parser()  # Default delimiters include space

#  Using .* - only matches within a single token
parser.add_var("wrong", rf"(?<match>d.*)")  # Matches only "def"

#  Using character classes - matches across tokens
parser.add_var("correct", rf"(?<match>d[a-z ]*i)")  # Matches "def ghi"
parser.compile()

event = parser.parse_event("abc def ghi")
print(event['match'])  # Output: "def ghi"
```

**Key Rule:** Character classes like `[a-zA-Z]*`, `[a-z ]*`, or `[\w\s]*` can match across token
boundaries, but `.*` cannot.

#### Alternation

Alternation (`|`) works as expected in log-surgeon, with concatenation binding more tightly than alternation (standard regex precedence).

```python
from log_surgeon import Parser

parser = Parser()

# Alternation works as expected: matches "abc" OR "def"
parser.add_var("word", rf"(?<word>abc|def)")

# Log levels: matches "ERROR" OR "WARN" OR "INFO"
parser.add_var("level", rf"(?<level>ERROR|WARN|INFO)")

# Status values: matches "success" OR "failure"
parser.add_var("status", rf"(?<status>success|failure)")

parser.compile()
```

You can use parentheses for grouping when needed:

```python
# Optional prefix with alternation
parser.add_var("msg", rf"(?<msg>(error|warn): .+)")

# Complex patterns
parser.add_var("id", rf"(?<id>(user|admin)_\d+)")
```

#### Optional patterns and quantifiers

log-surgeon supports standard regex quantifiers:

| Quantifier | Meaning |
|------------|---------|
| `?` | 0 or 1 (optional) |
| `*` | 0 or more |
| `+` | 1 or more |
| `{n}` | Exactly n |
| `{n,m}` | Between n and m |

```python
from log_surgeon import Parser

parser = Parser()

#  Use ? for optional patterns (matches 0 or 1)
parser.add_var("optional1", rf"(?<level>ERROR|WARN)?")  # Matches 0 or 1 occurrence

#  {0,1} is equivalent to ?
parser.add_var("optional2", rf"(?<level>ERROR|WARN){0,1}")  # Also matches 0 or 1 occurrence

#  Use * for 0 or more occurrences
parser.add_var("digits", rf"(?<num>\d*)")  # Matches 0 or more digits

#  Use + for 1 or more occurrences
parser.add_var("word", rf"(?<word>\w+)")  # Matches 1 or more word characters
parser.compile()
```

**Best practice:** Use `?` or `{0,1}` for optional elements (0 or 1 occurrences). Use `*` for 0 or more, and `+` for 1 or more.

#### Regex shorthands

log-surgeon supports common regex character class shorthands:

| Shorthand | Meaning | Equivalent |
|-----------|---------|------------|
| `\d` | Digit | `[0-9]` |
| `\D` | Non-digit | `[^0-9]` |
| `\s` | Whitespace | `[ \t\n\r\v\f]` |
| `\S` | Non-whitespace | `[^ \t\n\r\v\f]` |
| `\w` | Word character | `[a-zA-Z0-9_]` |
| `\W` | Non-word character | `[^a-zA-Z0-9_]` |

```python
from log_surgeon import Parser

parser = Parser()

# Using shorthands for cleaner patterns
parser.add_var("number", rf"(?<num>\d+)")           # Matches digits
parser.add_var("word", rf"(?<word>\w+)")            # Matches word characters
parser.add_var("trimmed", rf"(?<text>\S+)")         # Matches non-whitespace

parser.compile()
```

These shorthands can be used standalone, in character classes, or combined with quantifiers:

```python
# In character classes
parser.add_var("alphanumeric", rf"(?<id>[\w-]+)")   # Word chars + hyphen

# Combined with quantifiers
parser.add_var("optional_num", rf"(?<num>\d+)?")    # Optional digits
```

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

### Named capture groups

Use named capture groups in regex patterns to extract specific fields:

```python
parser.add_var("metric", rf"metric=(?<metric_name>\w+) value=(?<value>\d+)")
```

The syntax `(?<name>pattern)` creates a capture group that can be accessed as `event['name']`.

**Note:** See [Using Raw f-strings](#using-raw-f-strings-for-regex-patterns) for best practices on
writing regex patterns.

### Variable priority and ordering

Variable order in the schema determines matching precedence. Variables that appear first in the schema take precedence over those that appear later. Use the `priority` parameter to control this ordering:

> **Note:** Timestamps added via `add_timestamp()` always appear first in the schema and cannot be reordered with priority. Priority only controls the ordering of variables added via `add_var()`.

```python
from log_surgeon import Parser, PATTERN

parser = Parser()

# Timestamps are always first (added via add_timestamp)
parser.add_timestamp("ts", r"\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2}")

# High priority - specific patterns should match first
parser.add_var("ip_address", rf"(?<ip>{PATTERN.IPV4})", priority=5)
parser.add_var("specific_id", rf"ID(?<id>\d{{6}})", priority=5)

# Default priority (0) - normal patterns
parser.add_var("user_id", rf"user=(?<user>[a-zA-Z0-9]+)")
parser.add_var("status", rf"status=(?<status>[a-z]+)")

# Low priority (negative) - generic fallback patterns
parser.add_var("generic_float", rf"(?<float>{PATTERN.FLOAT})", priority=-1)
parser.add_var("generic_int", rf"(?<int>\d+)", priority=-2)

parser.compile()
```

**How priority works:**
- **Higher values appear first** in the schema (higher = higher precedence)
- **Default priority is 0** for normal patterns
- **Negative values** for generic/fallback patterns (more negative = lower priority)
- **Same priority** variables maintain insertion order

**Example ordering in compiled schema:**
```
[Timestamps always first - added via add_timestamp()]
priority=5:   ip_address, specific_id (insertion order)
priority=0:   user_id, status (insertion order)
priority=-1:  generic_float
priority=-2:  generic_int (matches last)
```

**Why this matters:** Without priority control, a generic `\d+` pattern added first could match "192" or specific IDs before your specific patterns get a chance. With priorities, you ensure specific patterns try to match before generic ones.

**Important:** Timestamps (added with `add_timestamp()`) are special anchoring patterns that always appear first in the schema, regardless of priority values.

### Using raw f-strings for regex patterns

> **⚠️ STRONGLY RECOMMENDED: Use raw f-strings (`rf"..."`) for all regex patterns.**
>
> While not absolutely required, using regular strings will likely cause escaping issues and pattern
failures. Raw f-strings prevent these problems.

Raw f-strings combine the benefits of:
- **Raw strings (`r"..."`)**: No need to double-escape regex special characters like `\d`, `\w`,
  `\n`
- **f-strings (`f"..."`)**: Easy interpolation of variables and pattern constants

#### Why use raw f-strings?

```python
#  Without raw strings - requires double-escaping
parser.add_var("metric", "value=(\\d+)")  # Hard to read, error-prone

#  With raw f-strings - single escaping, clean and readable
parser.add_var("metric", rf"value=(?<value>\d+)")
```

#### Watch out for braces in f-strings

When using f-strings, literal `{` and `}` characters must be escaped by doubling them:

```python
from log_surgeon import Parser, Pattern

parser = Parser()

#  Correct: Escape literal braces in regex
parser.add_var("json", rf"data={{(?<content>[^}}]+)}}")  # Matches: data={...}
parser.add_var("range", rf"range={{(?<min>\d+),(?<max>\d+)}}")  # Matches: range={10,20}

#  Using Pattern constants with interpolation
parser.add_var("ip", rf"IP: (?<ip>{Pattern.IPV4})")
parser.add_var("float", rf"value=(?<val>{Pattern.FLOAT})")

#  Common regex patterns
parser.add_var("digits", rf"\d+ items")  # No double-escaping needed
parser.add_var("word", rf"name=(?<name>\w+)")
parser.add_var("whitespace", rf"split\s+by\s+spaces")

parser.compile()
```

#### Examples: raw f-strings vs regular strings

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

Using regular strings (`"..."`) will require double-escaping (e.g., `"\\d+"`) which is error-prone
and can be hard to read.

### Schema Format

The schema defines delimiters, timestamps, and variables for parsing:

```
// schema delimiters
delimiters: \t\r\n:,!;%@/()[]

// schema timestamps
timestamp:<timestamp_regex>

// schema variables
variable_name:<variable_regex>
```

When using the fluent API (`Parser.add_var()` and `Parser.compile()`), the schema is built automatically.

### Common Pitfalls

 **Pattern doesn't match anything**
- Check: Are you using `.*` to match across tokens? Use `[a-zA-Z ]*` instead
- Check: Did you forget to call `parser.compile()`?
- Check: Are your delimiters splitting tokens unexpectedly?

 **Pattern works in regex tester but not here**
- Remember: log-surgeon is token-based, not character-based
- Traditional regex engines match across entire strings
- log-surgeon matches within token boundaries (delimited by spaces, colons, etc.)
- Read: [Token-Based Parsing](#token-based-parsing-and-delimiters)

 **Escape sequence errors in Python**
- Problem: `parser.add_var("digits", "(?<num>\d+)")` raises SyntaxError
- Solution: Use `rf"..."` (raw f-string) instead of `"..."` or `f"..."`
- Example: `parser.add_var("digits", rf"(?<num>\d+)")`

 **Optional patterns and quantifiers**
- `?` matches 0 or 1 occurrences (equivalent to `{0,1}`)
- `*` matches 0 or more occurrences
- `+` matches 1 or more occurrences
- Example: `(?<level>ERROR|WARN)?` for optional log level

---

## Reference

| Task                | Syntax                                       |
|---------------------|----------------------------------------------|
| Named capture       | `(?<name>pattern)`                           |
| Alternation         | `(?<name>opt1\|opt2)` or `(opt1)\|(opt2)`    |
| Optional (0 or 1)   | `?` or `{0,1}`                               |
| Match across tokens | Use `[a-z ]*` (NOT `.*`)                     |
| Pattern string      | `rf"..."` (raw f-string recommended)         |
| Log type            | `.select(["@log_type"])`                     |
| Original message    | `.select(["@log_message"])`                  |

### Parser

High-level parser for extracting structured data from unstructured log messages.

#### Constructor

- `Parser(delimiters: str = r" \t\r\n:,!;%@/()[]")`
  - Initialize a parser with optional custom delimiters
  - Default delimiters include space, tab, newline, and common punctuation
  - Note: Special characters no longer need to be escaped (as of log-surgeon 0.7.0)

#### Methods

- `add_var(name: str, regex: str, priority: int = 0) -> Parser`
  - Add a variable pattern to the parser's schema
  - Supports named capture groups using `(?<name>)` syntax
  - `priority`: Controls ordering in schema (higher values appear first, default is 0)
    - Use negative values for generic patterns (e.g., -1, -2, etc. where more negative = lower priority)
    - Variables with same priority maintain insertion order
  - Use raw f-strings (`rf"..."`) for regex patterns (see [Using Raw f-strings](#using-raw-f-strings-for-regex-patterns))
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

### LogEvent

Represents a parsed log event with extracted variables.

#### Methods

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

### JsonParser

Parser for JSON-formatted logs that extracts variables from string fields and merges them back into the original JSON.

> **Note:** Extraction only works on string-type fields. Non-string fields (numbers, booleans, objects, arrays) are skipped during extraction.

#### Constructor

- `JsonParser(parser: Parser)`
  - Initialize with a configured and compiled Parser instance
  - The Parser defines the extraction patterns to apply to JSON fields
  - By default, extracts from all string fields (equivalent to `target_fields("*")`)

#### Methods

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

### ConflictStrategy

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

### SchemaCompiler

Compiler for constructing log-surgeon schema definitions.

#### Constructor

- `SchemaCompiler(delimiters: str = DEFAULT_DELIMITERS)`
  - Initialize a schema compiler with optional custom delimiters

#### Methods

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

### PATTERN

Collection of pre-built regex patterns optimized for log parsing. These patterns follow log-surgeon's syntax requirements and are ready to use with named capture groups.

#### Available Patterns

**Network Patterns**

| Pattern | Description | Example Match |
|---------|-------------|---------------|
| `PATTERN.UUID` | UUID (Universally Unique Identifier) | `550e8400-e29b-41d4-a716-446655440000` |
| `PATTERN.IP_OCTET` | Single IPv4 octet (0-255) | `192`, `10`, `255` |
| `PATTERN.IPV4` | IPv4 address | `192.168.1.1`, `10.0.0.1` |
| `PATTERN.PORT` | Network port number (1-5 digits) | `80`, `8080`, `65535` |

**Numeric Patterns**

| Pattern | Description | Example Match |
|---------|-------------|---------------|
| `PATTERN.INT` | Integer with optional negative sign | `42`, `-123`, `0` |
| `PATTERN.FLOAT` | Float with optional negative sign | `3.14`, `-123.456`, `0.5` |

**File System Patterns**

| Pattern | Description | Example Match |
|---------|-------------|---------------|
| `PATTERN.LINUX_FILE_NAME_CHARSET` | Character set for Linux file names | `a-zA-Z0-9 ._-` |
| `PATTERN.LINUX_FILE_NAME` | Linux file name | `app.log`, `config-2024.yaml` |
| `PATTERN.LINUX_FILE_PATH` | Linux file path (relative) | `logs/app.log`, `var/log/system.log` |

**Character Sets and Word Patterns**

| Pattern | Description | Example Match |
|---------|-------------|---------------|
| `PATTERN.JAVA_IDENTIFIER_CHARSET` | Java identifier character set | `a-zA-Z0-9_` |
| `PATTERN.JAVA_IDENTIFIER` | Java identifier | `myVariable`, `$value`, `Test123` |
| `PATTERN.LOG_LINE_CHARSET` | Common log line characters | Alphanumeric + symbols + whitespace |
| `PATTERN.LOG_LINE` | General log line content | `Error: connection timeout` |
| `PATTERN.LOG_LINE_NO_WHITE_SPACE_CHARSET` | Log line chars without whitespace | Alphanumeric + symbols only |
| `PATTERN.LOG_LINE_NO_WHITE_SPACE` | Log content without spaces | `ERROR`, `/var/log/app.log` |

**Java-Specific Patterns**

| Pattern | Description | Example Match |
|---------|-------------|---------------|
| `PATTERN.JAVA_LITERAL_CHARSET` | Java literal character set | `a-zA-Z0-9_$` |
| `PATTERN.JAVA_PACKAGE_SEGMENT` | Single Java package segment | `com.`, `example.` |
| `PATTERN.JAVA_CLASS_NAME` | Java class name | `MyClass`, `ArrayList` |
| `PATTERN.JAVA_FULLY_QUALIFIED_CLASS_NAME` | Fully qualified class name | `java.util.ArrayList` |
| `PATTERN.JAVA_LOGGING_CODE_LOCATION_HINT` | Java logging location hint | `~[MyClass.java:42?]` |
| `PATTERN.JAVA_STACK_LOCATION` | Java stack trace location | `java.util.ArrayList.add(ArrayList.java:123)` |

#### Example usage

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

#### Composing Patterns

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

---

## Development

### Prerequisites

- **Python 3.9+**
- **C++20 compatible compiler**
  - Linux: GCC 10+ or Clang 10+
  - macOS: Xcode 14+ (install with `xcode-select --install`)
- **CMake 3.15+**
  - Linux: `apt install cmake` or `dnf install cmake`
  - macOS: `brew install cmake` or included with Xcode

### Building from source

```bash
# Clone the repository with submodules
git clone --recursive https://github.com/y-scope/log-surgeon-ffi-py.git
cd log-surgeon-ffi-py

# Install taskfile (dependency manager)
sh -c "$(curl -sSL https://taskfile.dev/install.sh)" -- -d
export PATH="$PWD/bin:$PATH"

# Install C++ dependencies (log-surgeon, fmt, Microsoft.GSL)
task deps:install-all

# Install in editable mode for development
pip install -e .
```

### macOS Development Setup

On macOS, you'll need to install CMake and set up a virtual environment due to externally-managed Python installations (Python 3.14+).

#### Step 1: Install CMake

```bash
# Install CMake via Homebrew
brew install cmake
```

**Note:** The build system now supports macOS BSD tar natively. GNU tar (`gtar`) is optional and not required.

#### Step 2: Set up a virtual environment

macOS Python from Homebrew is externally managed and requires using a virtual environment:

```bash
# Create a virtual environment
python3 -m venv venv

# Activate the virtual environment
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip
```

#### Step 3: Install dependencies and build

```bash
# Clone the repository with submodules
git clone --recursive https://github.com/y-scope/log-surgeon-ffi-py.git
cd log-surgeon-ffi-py

# Install taskfile (dependency manager)
sh -c "$(curl -sSL https://taskfile.dev/install.sh)" -- -d
export PATH="$PWD/bin:$PATH"

# Install C++ dependencies (log-surgeon, fmt, Microsoft.GSL)
task deps:install-all

# Install in editable mode for development
pip install -e .
```

#### Step 4: Verify installation

```bash
python -c "from log_surgeon import Parser; print('Installation successful!')"
```

#### Building a wheel on macOS

```bash
# Ensure virtual environment is activated
source venv/bin/activate

# Build a wheel for your current Python version
pip wheel . --no-deps -w dist/

# Install the wheel
pip install dist/*.whl

# Verify
python -c "from log_surgeon import Parser; print('Success!')"
```

### Building a wheel

```bash
# Build a wheel for your current Python version
pip wheel . --no-deps -w dist/

# The wheel will be in dist/
ls dist/*.whl
```

To build wheels matching CI output (using cibuildwheel):

```bash
# Install cibuildwheel
pip install cibuildwheel

# Build for a specific Python version (e.g., Python 3.12)
# Linux: cp312-manylinux_x86_64
# macOS: cp312-macosx_universal2
cibuildwheel --only cp312-macosx_universal2

# Wheels will be in wheelhouse/
ls wheelhouse/*.whl
```

### Running tests

```bash
# Install test dependencies
pip install pytest

# Run tests
python -m pytest tests/
```

### Linting and type checking

```bash
# Install dev dependencies
pip install ruff mypy

# Run linter
ruff check src/

# Run type checker
mypy src/
```

---

## License

Apache License 2.0 - See [LICENSE](LICENSE) for details.

---

## Links

- [Homepage](https://github.com/y-scope/log-surgeon-ffi-py)
- [Bug Tracker](https://github.com/y-scope/log-surgeon-ffi-py/issues)
- [log-surgeon C++ library](https://github.com/y-scope/log-surgeon)

---

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
