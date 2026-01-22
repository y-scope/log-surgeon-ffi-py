# log-surgeon-ffi

Python FFI bindings for [log-surgeon](https://github.com/y-scope/log-surgeon), a high-performance C++ library for extracting structured data from unstructured logs.

## Why log-surgeon?

With log-surgeon, you define variable patterns using regex with named capture groups. Variables can shift position, appear multiple times, or change order—log-surgeon handles this by compiling patterns into a DFA (deterministic finite automaton) for efficient single-pass parsing.

As variables are extracted, log-surgeon generates log templates (log types) by replacing matched values with placeholders, enabling pattern-based log analysis.

## Key Capabilities

- **Extract variables** from log messages using regex patterns with named capture groups.
- **Generate log types** (templates) automatically for log analysis.
- **Parse streams** efficiently for large-scale log processing.
- **Export data** to pandas DataFrames and PyArrow Tables.

## Quick Example

```python
from log_surgeon import Parser, PATTERN

parser = Parser()
parser.add_var("resource", rf"(?<memory_gb>{PATTERN.FLOAT}) GiB ram")
parser.compile()

event = parser.parse_event("Registering worker with 4.0 GiB ram\n")
print(event['memory_gb'])  # Output: 4.0
```

## Next Steps

- [Getting Started](getting-started.md) - Installation and first steps.
- [Key Concepts](key-concepts.md) - Understand delimiter-based matching.
- [API Reference](api-reference.md) - Complete API documentation.
