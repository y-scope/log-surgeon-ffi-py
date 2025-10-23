"""Multiple capture groups example: Extract platform metadata and application data."""

from log_surgeon import Parser

# Example 2: Extract multiple capture groups (platform metadata + application data)
parser = Parser()
parser.add_var(
    "platform",
    r"(?<platform_level>(INFO)|(WARN)|(ERROR)) \[(?<platform_thread>.+)\] "
    r"(?<platform_component>.+):",
)
parser.add_var(
    "memoryStore",
    r"MemoryStore started with capacity (?<memory_store_capacity_GiB>\d+\.\d+) GiB",
)
parser.compile()

event = parser.parse_event(
    " INFO [main] MemoryStore: MemoryStore started with capacity 7.0 GiB\n"
)

print("Example 2: Multiple capture groups")
if event:
    print(f"Message: {event.get_log_message().strip()}")
    print(f"LogType: {event.get_log_type()}")
    print(f"Capture groups: {event}")
