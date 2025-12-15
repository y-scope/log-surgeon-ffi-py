"""Multiple capture groups example: Extract data from complex multi-line Java stack trace."""

from log_surgeon import PATTERN, Parser

# Parse a sample log event with stack trace
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

# Create a parser and define extraction patterns
parser = Parser()

# Add timestamp pattern
parser.add_timestamp("TIMESTAMP_SPARK_1_6", rf"\d{{2}}/\d{{2}}/\d{{2}} \d{{2}}:\d{{2}}:\d{{2}}")

# Add variable patterns
parser.add_var("SYSTEM_LEVEL", rf"(?<level>INFO|WARN|ERROR)")
parser.add_var(
    "SPARK_HOST_IP_PORT",
    rf"(?<spark_host>spark\-{PATTERN.INT})/(?<system_ip>{PATTERN.IPV4}):(?<system_port>{PATTERN.PORT})",
)
parser.add_var(
    "SYSTEM_EXCEPTION",
    rf"(?<system_exception_type>({PATTERN.JAVA_PACKAGE_SEGMENT})+[{PATTERN.JAVA_IDENTIFIER_CHARSET}]*Exception): "
    rf"(?<system_exception_msg>{PATTERN.LOG_LINE})",
)
parser.add_var(
    "SYSTEM_STACK_TRACE",
    rf"(\s{{1,4}}at (?<system_stack>{PATTERN.JAVA_STACK_LOCATION})",
)
parser.compile()

# Parse a single event
event = parser.parse_event(log_line)

# Access extracted data
print(f"Message: {event.get_log_message().strip()}")
print(f"LogType: {event.get_log_type().strip()}")
print(f"Parsed Logs: {event}")
