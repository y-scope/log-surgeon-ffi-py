# log-surgeon-ffi

`log-surgeon-ffi` provides Python foreign function interface (FFI) bindings for
[`log-surgeon`](https://github.com/y-scope/log-surgeon).

---

## Quick navigation

[**Overview**](#overview) · [**Getting started**](#getting-started) · [**Documentation**](#documentation)

---

## Overview

`log-surgeon-ffi` provides Python bindings for [`log-surgeon`](https://github.com/y-scope/log-surgeon),
a high-performance library for extracting structured data from unstructured logs. It supports both
C++ and Rust backend engines.

### Why `log-surgeon`?

With `log-surgeon`, you define variable patterns using regex with named capture groups. Variables can
shift position, appear multiple times, or change order—`log-surgeon` handles this by compiling
patterns into a DFA (deterministic finite automaton) for efficient single-pass parsing.

As variables are extracted, `log-surgeon` generates log templates (log types) by replacing matched
values with placeholders, enabling pattern-based log analysis.

### Key capabilities

* **Extract variables** from log messages using regex patterns with named capture groups
* **Generate log types** (templates) automatically for log analysis
* **Parse streams** efficiently for large-scale log processing
* **Export data** to pandas DataFrames and PyArrow Tables

### When to use `log-surgeon`

**Good fit**
* Large-scale log processing.
* Extracting structured data from semi-structured logs.
* Generating log templates for analytics.
* Multi-line log events (stack traces, JSON dumps).
* Performance-critical parsing.

**Not ideal**
* Simple one-off text extraction (use Python `re` module).
* Highly irregular text where variable boundaries cannot be defined by patterns.
* Patterns requiring full PCRE features (lookahead, backreferences).

---

## Getting started

### Installation

```bash
pip install log-surgeon-ffi
```

Verify installation:
```bash
python -c "from log_surgeon import Parser; print('Installation successful.')"
```

### Before you start

> **Key difference from traditional regex:**
>
> In `log-surgeon`, `.` matches any character **except delimiters** (spaces, colons, etc.).
> This means `.*` stops at delimiter characters. To match text containing delimiters,
> use explicit character classes like `[a-zA-Z ]*`.
>
> See [Key Concepts](https://y-scope.github.io/log-surgeon-ffi-py/beta/key-concepts/) for details.

**Tip:** Use raw f-strings (`rf"..."`) for regex patterns to avoid escaping issues.

### Quick start

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

### More examples

See [`examples/`](examples/) for runnable scripts:

| Example | Description |
|---------|-------------|
| [`basic_parsing.py`](examples/basic_parsing.py) | Extract variables with PATTERN constants |
| [`multiple_capture_groups.py`](examples/multiple_capture_groups.py) | Parse multi-line Java stack traces |
| [`export_to_dataframe.py`](examples/export_to_dataframe.py) | Export parsed logs to pandas DataFrame |
| [`filtering_events.py`](examples/filtering_events.py) | Filter events with lambda predicates |
| [`json_log_parsing.py`](examples/json_log_parsing.py) | Parse JSON-formatted logs |

---

## Documentation

**[Full Documentation](https://y-scope.github.io/log-surgeon-ffi-py/beta/)** — includes:

- [Key Concepts](https://y-scope.github.io/log-surgeon-ffi-py/beta/key-concepts/) — Delimiter-based matching, capture groups, priority.
- [API Reference](https://y-scope.github.io/log-surgeon-ffi-py/beta/api-reference/) — Parser, Query, JsonParser, PATTERN constants.
- [Architecture](https://y-scope.github.io/log-surgeon-ffi-py/beta/architecture/) — Internal design, component layers, data flow.
- [Development](https://y-scope.github.io/log-surgeon-ffi-py/beta/development/) — Building from source, testing, linting.

---

## Backend Engines

`log-surgeon-ffi` supports two backend engines:

| Backend | Description |
|---------|-------------|
| **C++** (default) | The original [log-surgeon](https://github.com/y-scope/log-surgeon) C++ library via pybind11. |
| **Rust** | The [log-mechanic](https://github.com/y-scope/log-surgeon) Rust implementation via cffi. |

Select a backend via the `backend` parameter or the `LOG_SURGEON_BACKEND` environment variable:

```python
# Via constructor parameter
parser = Parser(backend="rust")

# Via environment variable (applies to all Parser instances)
# export LOG_SURGEON_BACKEND=rust
parser = Parser()  # Uses Rust backend
```

Both backends share the same Python API. The Rust backend is under active development and
may have minor behavioral differences—see [Key Concepts](https://y-scope.github.io/log-surgeon-ffi-py/beta/key-concepts/) for details.

---

## License

Apache License 2.0 - See [LICENSE](LICENSE) for details.

---

## Links

- [Documentation](https://y-scope.github.io/log-surgeon-ffi-py/beta/)
- [Homepage](https://github.com/y-scope/log-surgeon-ffi-py)
- [Bug Tracker](https://github.com/y-scope/log-surgeon-ffi-py/issues)
- [log-surgeon C++ library](https://github.com/y-scope/log-surgeon)

---

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
