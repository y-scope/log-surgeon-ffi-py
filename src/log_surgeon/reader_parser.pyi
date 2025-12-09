from typing import IO

from .log_event import LogEvent

class ReaderParser:
    def __init__(
        self,
        input_stream: IO[bytes],
        schema_content: str,
        debug: bool = False,
    ) -> None: ...
    def parse_next_log_event(self) -> LogEvent | None: ...
    def reset_input_stream(self, input_stream: IO[bytes]) -> bool: ...
    def done(self) -> bool: ...
