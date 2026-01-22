# Getting Started

## Installation

```bash
pip install log-surgeon-ffi
```

Verify installation:

```bash
python -c "from log_surgeon import Parser; print('Installation successful.')"
```

## Before You Start

!!! warning "Key difference from traditional regex"
    In log-surgeon, `.` matches any character **except delimiters** (spaces, colons, etc.).
    This means `.*` stops at delimiter characters. To match text containing delimiters,
    use explicit character classes like `[a-zA-Z ]*`.

    See [Key Concepts](key-concepts.md) for details.

**Tip:** Use raw f-strings (`rf"..."`) for regex patterns to avoid escaping issues.

## Quick Start

```python
from log_surgeon import Parser, PATTERN

# Parse a sample log event
log_line = "16/05/04 04:24:58 INFO Registering worker with 1 core and 4.0 GiB ram\n"

# Create a parser and define extraction patterns
parser = Parser()
parser.add_var("resource", rf"(?<memory_gb>{PATTERN.FLOAT}) GiB ram")
parser.compile()

# Parse and extract
event = parser.parse_event(log_line)
print(f"LogType: {event.get_log_type().strip()}")
print(f"memory_gb = {event['memory_gb']}")
```

**Output:**

```
LogType: 16/05/04 04:24:58 INFO Registering worker with 1 core and <memory_gb> GiB ram
memory_gb = 4.0
```

## Examples

See the [`examples/`](https://github.com/y-scope/log-surgeon-ffi-py/tree/main/examples) directory for runnable scripts:

| Example | Description |
|---------|-------------|
| `basic_parsing.py` | Extract variables with PATTERN constants. |
| `multiple_capture_groups.py` | Parse multi-line Java stack traces. |
| `export_to_dataframe.py` | Export parsed logs to pandas DataFrame. |
| `filtering_events.py` | Filter events with lambda predicates. |
| `json_log_parsing.py` | Parse JSON-formatted logs. |

## When to Use log-surgeon

**Good fit:**

- Large-scale log processing.
- Extracting structured data from semi-structured logs.
- Generating log templates for analytics.
- Multi-line log events (stack traces, JSON dumps).
- Performance-critical parsing.

**Not ideal:**

- Simple one-off text extraction (use Python `re` module).
- Highly irregular text where variable boundaries cannot be defined by patterns.
- Patterns requiring full PCRE features (lookahead, backreferences).
