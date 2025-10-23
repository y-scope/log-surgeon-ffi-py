"""Query example: Extract metrics from logs and export to DataFrame and Arrow Table."""

from log_surgeon import Parser, Query

# Example: Extract metrics from logs and export to DataFrame
parser = Parser()
parser.add_var(
    "memoryStore",
    r"MemoryStore started with capacity (?<memory_store_capacity_GiB>\d+\.\d+) GiB",
)
parser.compile()

log_data = " INFO [main] MemoryStore: MemoryStore started with capacity 7.0 GiB"

query = (
    Query(parser)
    .select(["@log_type", "@log_message", "*"])
    .from_(log_data)
    .validate_query()
)

# Export to pandas DataFrame
df = query.to_dataframe()
print("DataFrame:")
print(df)
print()

# Reset stream for second export
query.from_(log_data)

# Export to PyArrow Table
arrow_table = query.to_arrow()
print("Arrow Table:")
print(arrow_table)
