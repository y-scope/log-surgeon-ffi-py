"""Export to DataFrame example: Query and export parsed logs to pandas DataFrame."""

from log_surgeon import Parser, Query

parser = Parser()
parser.add_var("metric", rf"metric=(?<metric_name>\w+) value=(?<value>\d+)")
parser.compile()

log_data = """
2024-01-01 INFO: metric=cpu value=42
2024-01-01 INFO: metric=memory value=100
2024-01-01 INFO: metric=disk value=7
"""

# Create a query and export to DataFrame
query = Query(parser).select(["metric_name", "value"]).from_(log_data).validate_query()

df = query.to_dataframe()
print(df)
