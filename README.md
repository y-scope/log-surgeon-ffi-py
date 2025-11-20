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
* [Using raw f-strings for regex patterns](#using-raw-f-strings-for-regex-patterns)

[**Reference**](#reference)
* [Parser API](#parser)
* [Query API](#query)
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
> * `abc|def` requires grouping: use `(abc)|(def)` instead
> * Use `{0,1}` for optional patterns, NOT `?`
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
parser.add_var("SYSTEM_LEVEL", rf"(?<level>(INFO)|(WARN)|(ERROR))")
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
parser.add_var("SYSTEM_LEVEL", rf"(?<level>(INFO)|(WARN)|(ERROR))")
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

#### Alternation requires grouping

**CRITICAL:** Alternation (`|`) works differently in log-surgeon compared to traditional regex
engines. You **must** use parentheses to group alternatives.

```python
from log_surgeon import Parser

parser = Parser()

#  WRONG: Without grouping - matches "ab" AND ("c" OR "d") AND "ef"
parser.add_var("wrong", rf"(?<word>abc|def)")
# In log-surgeon, this is interpreted as: "ab" + "c|d" + "ef"
# Matches: "abcef" or "abdef" (NOT "abc" or "def")

#  CORRECT: With grouping - matches "abc" OR "def"
parser.add_var("correct", rf"(?<word>(abc)|(def))")
# Matches: "abc" or "def"
parser.compile()
```

**In traditional regex engines**, `abc|def` means "abc" OR "def".
**In log-surgeon**, `abc|def` means "ab" + ("c" OR "d") + "ef".

**Key Rule:** Always use `(abc)|(def)` syntax for alternation to match complete alternatives.

```python
# More examples:
parser.add_var("level", rf"(?<level>(ERROR)|(WARN)|(INFO))")  #  Correct
parser.add_var("status", rf"(?<status>(success)|(failure))")  #  Correct
parser.add_var("bad", rf"(?<status>success|failure)")         #  Wrong - unexpected behavior
```

#### Optional patterns

For optional patterns, use `{0,1}` instead of `*`:

```python
from log_surgeon import Parser

parser = Parser()

#  Avoid using * for optional patterns (matches 0 or more)
parser.add_var("avoid", rf"(?<level>(ERROR)|(WARN))*")  # Can match empty string or multiple reps

#  Do not use ? for optional patterns
parser.add_var("avoid2", rf"(?<level>(ERROR)|(WARN))?")  # May not work as expected

#  Use {0,1} for optional patterns (matches 0 or 1)
parser.add_var("optional", rf"(?<level>(ERROR)|(WARN)){0,1}")  # Matches 0 or 1 occurrence
parser.compile()
```

**Best practice:** Use `{0,1}` for optional elements. Avoid `*` (0 or more) and `?` for optional
matching.

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

### Logical vs. physical names

Internally, log-surgeon uses "physical" names (e.g., `CGPrefix0`, `CGPrefix1`) for capture groups,
while you work with "logical" names (e.g., `user_id`, `thread`). The `GroupNameResolver` handles
this mapping automatically.

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

 **Alternation not working (abc|def)**
- Problem: `(?<name>abc|def)` doesn't match "abc" or "def" as expected
- Solution: Use `(?<name>(abc)|(def))` with explicit grouping

 **Pattern works in regex tester but not here**
- Remember: log-surgeon is token-based, not character-based
- Traditional regex engines match across entire strings
- log-surgeon matches within token boundaries (delimited by spaces, colons, etc.)
- Read: [Token-Based Parsing](#token-based-parsing-and-delimiters)

 **Escape sequence errors in Python**
- Problem: `parser.add_var("digits", "(?<num>\d+)")` raises SyntaxError
- Solution: Use `rf"..."` (raw f-string) instead of `"..."` or `f"..."`
- Example: `parser.add_var("digits", rf"(?<num>\d+)")`

 **Optional pattern matching incorrectly**
- Problem: Using `?` or `*` for optional patterns
- Solution: Use `{0,1}` for optional elements
- Example: `(?<level>(ERROR)|(WARN)){0,1}` for optional log level

---

## Reference

| Task                | Syntax                                       |
|---------------------|----------------------------------------------|
| Named capture       | `(?<name>pattern)`                           |
| Alternation         | `(?<name>(opt1)\|(opt2))` NOT `(opt1\|opt2`) |
| Optional            | `{0,1}` (NOT `?` or `*`)                     |
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

- `add_var(name: str, regex: str, hide_var_name_if_named_group_present: bool = True) -> Parser`
  - Add a variable pattern to the parser's schema
  - Supports named capture groups using `(?<name>)` syntax
  - Use raw f-strings (`rf"..."`) for regex patterns (see [Using Raw f-strings](#using-raw-f-strings-for-regex-patterns))
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

### Building from source

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

### Running tests

```bash
# Install test dependencies
pip install pytest

# Run tests
python -m pytest tests/
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
