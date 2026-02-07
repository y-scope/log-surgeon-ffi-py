"""
Multiple capture groups example: Parse complex multi-line Java stack traces.

This example demonstrates advanced parsing features:
1. Timestamps for multi-line event boundaries
2. Multiple named capture groups in a single pattern
3. Repeated capture groups (automatically aggregated into arrays)
4. Composing patterns with PATTERN constants

Key concepts:
- add_timestamp(): Defines patterns that mark log event boundaries
- Multiple capture groups: Extract several fields from one pattern
- Array aggregation: Repeated matches become lists (e.g., stack trace lines)
- Double braces {{n}}: In f-strings, use {{ and }} to get literal { and } in regex
"""

from log_surgeon import PATTERN, Parser

# Multi-line log event with a Java stack trace
# Note: The timestamp "16/05/04 12:22:37" marks where this event starts
log_line = """16/05/04 12:22:37 WARN server.TransportChannelHandler: Exception in connection from spark-35/192.168.10.50:55392
java.io.IOException: Connection reset by peer
        at sun.nio.ch.FileDispatcherImpl.read0(Native Method)
        at sun.nio.ch.SocketDispatcher.read(SocketDispatcher.java:39)
        at sun.nio.ch.IOUtil.readIntoNativeBuffer(IOUtil.java:223)
        at sun.nio.ch.IOUtil.read(IOUtil.java:192)
        at sun.nio.ch.SocketChannelImpl.read(SocketChannelImpl.java:380)
        at io.netty.buffer.PooledUnsafeDirectByteBuf.setBytes(PooledUnsafeDirectByteBuf.java:313)
        at io.netty.buffer.AbstractByteBuf.writeBytes(AbstractByteBuf.java:881)
        at io.netty.channel.socket.nio.NioSocketChannel.doReadBytes(NioSocketChannel.java:242)
        at io.netty.channel.nio.AbstractNioByteChannel$NioByteUnsafe.read(AbstractNioByteChannel.java:119)
        at io.netty.channel.nio.NioEventLoop.processSelectedKey(NioEventLoop.java:511)
        at io.netty.channel.nio.NioEventLoop.processSelectedKeysOptimized(NioEventLoop.java:468)
        at io.netty.channel.nio.NioEventLoop.processSelectedKeys(NioEventLoop.java:382)
        at io.netty.channel.nio.NioEventLoop.run(NioEventLoop.java:354)
        at io.netty.util.concurrent.SingleThreadEventExecutor$2.run(SingleThreadEventExecutor.java:111)
        at java.lang.Thread.run(Thread.java:750)
"""

parser = Parser()

# === TIMESTAMP PATTERN ===
# Timestamps mark where new log events begin (important for multi-line logs)
#
# Pattern: \d{{2}}/\d{{2}}/\d{{2}} \d{{2}}:\d{{2}}:\d{{2}}
#
# Why {{2}} instead of {2}?
#   In f-strings, { and } are special characters for interpolation.
#   To get a literal {2} in the regex, we must escape as {{2}}.
#   This matches exactly 2 digits.
parser.add_timestamp(
    "TIMESTAMP_SPARK",
    rf"\d{{2}}/\d{{2}}/\d{{2}} \d{{2}}:\d{{2}}:\d{{2}}"
)

# === LOG LEVEL PATTERN ===
# Alternation: INFO|WARN|ERROR matches any of these three strings
parser.add_var("SYSTEM_LEVEL", rf"(?<level>INFO|WARN|ERROR)")

# === HOST/IP/PORT PATTERN ===
# Combines multiple capture groups and PATTERN constants:
#   (?<spark_host>spark\-{PATTERN.INT})  - "spark-" followed by an integer
#   (?<system_ip>{PATTERN.IPV4})         - IPv4 address like 192.168.10.50
#   (?<system_port>{PATTERN.PORT})       - Port number like 55392
#
# Note: \- escapes the hyphen (though not strictly necessary outside char classes)
parser.add_var(
    "SPARK_HOST_IP_PORT",
    rf"(?<spark_host>spark\-{PATTERN.INT})/(?<system_ip>{PATTERN.IPV4}):(?<system_port>{PATTERN.PORT})",
)

# === EXCEPTION PATTERN ===
# Captures exception type and message:
#   ({PATTERN.JAVA_PACKAGE_SEGMENT})+  - One or more package segments (e.g., "java.io.")
#   [...]*Exception                    - Class name ending in "Exception"
#   (?<system_exception_msg>...)       - Everything after ": " is the message
parser.add_var(
    "SYSTEM_EXCEPTION",
    rf"(?<system_exception_type>({PATTERN.JAVA_PACKAGE_SEGMENT})+[{PATTERN.JAVA_IDENTIFIER_CHARSET}]*Exception): "
    rf"(?<system_exception_msg>{PATTERN.LOG_LINE})",
)

# === STACK TRACE PATTERN ===
# This pattern matches each "at ..." line in the stack trace.
# Since it matches multiple times, the captured values become an ARRAY.
#
#   \s{{1,4}}                          - 1-4 whitespace characters (indentation)
#   at                                 - Literal "at "
#   (?<system_stack>{PATTERN.JAVA_STACK_LOCATION})  - Method location
#
# PATTERN.JAVA_STACK_LOCATION matches: "package.Class.method(File.java:123)"
parser.add_var(
    "SYSTEM_STACK_TRACE",
    rf"(\s{{1,4}}at (?<system_stack>{PATTERN.JAVA_STACK_LOCATION})",
)

parser.compile()

# Parse the multi-line event
event = parser.parse_event(log_line)

# Display results
print("=== Extracted Fields ===")
print(f"timestamp: {event['firstTimestamp']}")
print(f"level: {event['level']}")
print(f"spark_host: {event['spark_host']}")
print(f"system_ip: {event['system_ip']}")
print(f"system_port: {event['system_port']}")
print(f"exception_type: {event['system_exception_type']}")
print(f"exception_msg: {event['system_exception_msg']}")

# Stack trace is an ARRAY because the pattern matched multiple times
print(f"\nstack_trace ({len(event['system_stack'])} frames):")
for i, frame in enumerate(event["system_stack"][:3]):  # Show first 3
    print(f"  [{i}] {frame}")
print("  ...")

print("\n=== Log Type (Template) ===")
print(event.get_log_type().strip()[:200] + "...")

# Expected output (abbreviated):
# === Extracted Fields ===
# timestamp: 16/05/04 12:22:37
# level: WARN
# spark_host: spark-35
# system_ip: 192.168.10.50
# system_port: 55392
# exception_type: java.io.IOException
# exception_msg: Connection reset by peer
#
# stack_trace (15 frames):
#   [0] sun.nio.ch.FileDispatcherImpl.read0(Native Method)
#   [1] sun.nio.ch.SocketDispatcher.read(SocketDispatcher.java:39)
#   [2] sun.nio.ch.IOUtil.readIntoNativeBuffer(IOUtil.java:223)
#   ...
