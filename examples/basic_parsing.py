"""Basic parsing example: Extract a single capture group from a log message."""

from log_surgeon import PATTERN, Parser

# Parse a sample log event
log_line = "16/05/04 04:24:58 INFO Registering worker with 1 core and 4.0 GiB ram\n"

# Create a parser and define extraction patterns
parser = Parser()
parser.add_var("resource", rf"(?<memory_gb>{PATTERN.FLOAT}) GiB ram")
parser.compile()

# Parse a single event
event = parser.parse_event(log_line)

# Access extracted data
print(f"Message: {event.get_log_message().strip()}")
print(f"LogType: {event.get_log_type().strip()}")
print(f"Parsed Logs: {event}")
