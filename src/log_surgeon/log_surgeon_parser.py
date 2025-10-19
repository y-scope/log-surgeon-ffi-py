import io

from log_surgeon_ffi import ReaderParser


class LogSurgeonParser:
    def __init__(self):
        self.schema: str = None
        self.stream: Union[io.BytesIO, io.StringIO] = None
        self.paraser = None
        self.default_delimiters = "delimiters: \\t\\r\\n:,!;%@"

    def load_schema(self, schema: str) -> None:
        self.schema = f"{self.default_delimiters}\n{schema}"

    def load_schema_file(self, schema_file_path: str) -> None:
        with open(schema_file_path, "r") as schema_file:
            self.schema = f"{self.default_delimiters}\n{schema_file.read()}"
        self.stream = None

    def parse_string(self, payload: str):
        parser = ReaderParser(io.StringIO(payload), self.schema)
        event = parser.parse_next_log_event()
        return event


if __name__ == '__main__':
    parser = LogSurgeonParser()

    # Let's start simple with the input: " INFO [main] MemoryStore: MemoryStore started with capacity 7.0 GiB\n"
    # 1. identify and extract "7.0" from the log message
    # 2. label it as "MemoryStore.CapacityGiB"
    parser.load_schema("MemoryStore:MemoryStore started with capacity (?<MemoryStoreCapacityGiB>\d+\.\d+) GiB")
    event = parser.parse_string(" INFO [main] MemoryStore: MemoryStore started with capacity 7.0 GiB\n")
    print(f"MemoryStoreCapacityGiB:{event['MemoryStoreCapacityGiB']}")
