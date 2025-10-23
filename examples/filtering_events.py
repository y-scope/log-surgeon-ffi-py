"""Filtering events example: Filter log events based on field values."""

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
    .filter(lambda event: int(event["value"]) > 50)
    .validate_query()
)

df = query.to_dataframe()
print(df)
print("\nExpected output:")
print("  metric_name  value")
print("0      memory    100")
print("1         cpu     85")
