"""
Export to DataFrame example: Parse logs and export to pandas DataFrame.

This example demonstrates the Query API for structured data export:
1. Create and compile a Parser with extraction patterns
2. Use Query to select specific fields
3. Export results to a pandas DataFrame

Key concepts:
- Query builder: Fluent API for selecting and transforming parsed data
- Field selection: Choose which captured variables to include
- DataFrame export: Convert parsed logs to pandas for analysis
"""

from log_surgeon import Parser, Query

# Step 1: Create parser with extraction patterns
parser = Parser()

# Pattern breakdown:
#   metric=(?<metric_name>[a-zA-Z0-9_]+)  - Capture word characters after "metric=" as "metric_name"
#   value=(?<value>\d+)                   - Capture digits after "value=" as "value"
#
# [a-zA-Z0-9_]+ matches one or more "word characters" (letters, digits, underscore)
# \d+ matches one or more digits
parser.add_var("metric", rf"metric=(?<metric_name>[a-zA-Z0-9_]+) value=(?<value>\d+)")

# Compile is required before parsing
parser.compile()

# Sample log data (multi-line string)
log_data = """\
2024-01-01 INFO: metric=cpu value=42
2024-01-01 INFO: metric=memory value=100
2024-01-01 INFO: metric=disk value=7"""

# Step 2: Build a query using the fluent API
#
# Query(parser)           - Create query with the compiled parser
# .select([...])          - Choose which fields to extract
# .from_(log_data)        - Set the input source (string, file, or stream)
# .validate_query()       - Verify the query is valid before execution
query = (
    Query(parser)
    .select(["metric_name", "value"])  # Only include these two fields
    .from_(log_data)
    .validate_query()
)

# Step 3: Export to pandas DataFrame
df = query.to_dataframe()

print("=== Parsed Logs as DataFrame ===")
print(df)
print(f"\nDataFrame shape: {df.shape[0]} rows x {df.shape[1]} columns")
print(f"Columns: {list(df.columns)}")

# Expected output:
# === Parsed Logs as DataFrame ===
#   metric_name value
# 0         cpu    42
# 1      memory   100
# 2        disk     7
#
# DataFrame shape: 3 rows x 2 columns
# Columns: ['metric_name', 'value']
