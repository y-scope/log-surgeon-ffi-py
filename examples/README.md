# log-surgeon-ffi Examples

This directory contains example scripts demonstrating how to use log-surgeon-ffi. These examples correspond to the Quick Start examples in the main README.

## Running Examples

Each example can be run directly with Python:

```bash
python examples/basic_parsing.py
python examples/multiple_capture_groups.py
python examples/export_to_dataframe.py
python examples/filtering_events.py
python examples/json_log_parsing.py
```

To run with the Rust backend instead of the default C++ backend, set the
`LOG_SURGEON_BACKEND` environment variable:

```bash
LOG_SURGEON_BACKEND=rust python examples/basic_parsing.py
```

## Examples

### Parser Examples

- **`basic_parsing.py`** - Basic parsing with PATTERN constants
  - Extract a single capture group using PATTERN.FLOAT
  - Shows parser setup, compilation, and event extraction
  - Demonstrates accessing log message, log type, and parsed fields

- **`multiple_capture_groups.py`** - Complex multi-line parsing
  - Parse Java stack traces with multiple capture groups
  - Demonstrates timestamp-based event separation
  - Extracts scalar fields (level, IP, port) and array fields (stack traces)
  - Shows automatic aggregation of repeated capture groups

### JSON Parser Examples

- **`json_log_parsing.py`** - Parse JSON-formatted logs
  - Extract variables from JSON string fields
  - Demonstrates all conflict resolution strategies (NEST, PREFIX, OVERWRITE, RAISE)
  - Nested field access with dot-notation
  - NDJSON and JSON array format support
  - Integration with Query for DataFrame export
  - Default behavior (all string fields) and target field selection

### Query Examples

- **`export_to_dataframe.py`** - Export to pandas DataFrame
  - Use Query builder to select specific fields
  - Export parsed logs to pandas DataFrame
  - Demonstrates fluent query interface

- **`filtering_events.py`** - Filter log events
  - Apply filter predicate to select specific events
  - Shows lambda-based filtering
  - Export filtered results to DataFrame

## More Examples

For additional examples and use cases, see the main [README.md](../README.md) which includes:
- Stream parsing with timestamps
- Using pattern constants (IPV4, UUID, FLOAT, etc.)
- Including log type and message in output
- Analyzing log types and patterns
- Log type counting and sampling
