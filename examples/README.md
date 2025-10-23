# log-surgeon-ffi Examples

This directory contains example scripts demonstrating how to use log-surgeon-ffi.

## Running Examples

Each example can be run directly with Python:

```bash
python examples/parser_basic.py
python examples/parser_multiple_groups.py
python examples/query_dataframe_export.py
```

Or from the project root:

```bash
python -m examples.parser_basic
python -m examples.parser_multiple_groups
python -m examples.query_dataframe_export
```

## Examples

### Parser Examples

- **`parser_basic.py`** - Extract a single capture group from a log message
  - Shows basic parser setup and compilation
  - Demonstrates single variable extraction

- **`parser_multiple_groups.py`** - Extract multiple capture groups
  - Shows how to define multiple variables
  - Extracts both platform metadata and application data

### Query Examples

- **`query_dataframe_export.py`** - Export parsed logs to DataFrame and Arrow Table
  - Demonstrates query builder pattern
  - Shows exporting to pandas DataFrame
  - Shows exporting to PyArrow Table

## More Examples

For more comprehensive examples, see the main [README.md](../README.md) which includes:
- Stream parsing with timestamps
- Using pattern constants
- Filtering events
- Log type analysis
