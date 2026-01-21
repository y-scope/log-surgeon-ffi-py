"""
Filtering events example: Filter parsed log events based on field values.

This example demonstrates how to filter log events using Query.filter():
1. Create and compile a Parser with extraction patterns
2. Use Query.filter() with a lambda predicate
3. Export only matching events to DataFrame

Key concepts:
- Filter predicates: Lambda functions that return True/False for each event
- Event access: Use event['field_name'] to access captured values
- Type conversion: Captured values are strings; convert for numeric comparisons
"""

from log_surgeon import Parser, Query

# Step 1: Create parser with extraction patterns
parser = Parser()
parser.add_var("metric", rf"metric=(?<metric_name>\w+) value=(?<value>\d+)")
parser.compile()

# Sample log data with varying values
log_data = """
2024-01-01 INFO: metric=cpu value=42
2024-01-01 INFO: metric=memory value=100
2024-01-01 INFO: metric=disk value=7
2024-01-01 INFO: metric=cpu value=85
"""

# Step 2: Build query with a filter
#
# .filter() takes a predicate function that receives each LogEvent
# and returns True to include it, False to exclude it.
#
# Note: Captured values are always strings, so we convert to int for comparison
query = (
    Query(parser)
    .select(["metric_name", "value"])
    .from_(log_data)
    .filter(lambda event: int(event["value"]) > 50)  # Only events with value > 50
    .validate_query()
)

# Step 3: Export filtered results
df = query.to_dataframe()

print("=== Filtered Events (value > 50) ===")
print(df)

# You can also use more complex filter logic:
#
# Filter by metric name:
#   .filter(lambda e: e["metric_name"] == "cpu")
#
# Multiple conditions:
#   .filter(lambda e: e["metric_name"] == "cpu" and int(e["value"]) > 50)
#
# Using a named function:
#   def is_high_cpu(event):
#       return event["metric_name"] == "cpu" and int(event["value"]) > 80
#   .filter(is_high_cpu)

# Expected output:
# === Filtered Events (value > 50) ===
#   metric_name value
# 0      memory   100
# 1         cpu    85
