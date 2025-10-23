"""Basic parsing example: Extract a single capture group from a log message."""

from log_surgeon import Parser

# Example 1: Extract a single capture group from a log message
parser = Parser()
parser.add_var(
    "memoryStore",
    r"MemoryStore started with capacity (?<memory_store_capacity_GiB>\d+\.\d+) GiB",
)
parser.compile()

event = parser.parse_event(
    " INFO [main] MemoryStore: MemoryStore started with capacity 7.0 GiB\n"
)

print("Example 1: Basic parsing")
if event:
    print(f"Message: {event.get_log_message().strip()}")
    print(f"LogType: {event.get_log_type()}")
    print(f"Capture groups: {event}")
