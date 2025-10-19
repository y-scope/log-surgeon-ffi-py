import io
import pcre2

from log_surgeon_ffi import ReaderParser

DEFAULT_DELIMITERS = " \\t\\r\\n:,!;%@"

class LogSurgeonVariable:
    def __init__(self, name: str, regex: str, capture_group_names: set[str]) -> None:
        self.name = name
        self.regex = regex
        self.capture_group_names = capture_group_names

    def get_schema_variable_entry(self):
        return f"{self.name}:{self.regex}"


class LogSurgeonParser:
    def __init__(self, delimiters: str = DEFAULT_DELIMITERS):
        self.delimiters = delimiters
        self.decoded_delimiters = delimiters.encode().decode('unicode_escape')

        self.variables = []
        self.variable_names = {}
        self.capture_group_names = {}


    def add_schema_variable(self, name: str, regex: str) -> None:
        # Validate variable name
        if name in self.variable_names:
            raise AttributeError(f'Variable "{name}" already exists and must be unique.')
        if name in self.capture_group_names:
            raise AttributeError(
                f'Variable "{name}" cannot coexist with a capture group of the same name '
                f'already defined in variable "{self.capture_group_names[name].name}".'
            )
        if any(char in name for char in self.decoded_delimiters):
            raise ValueError(
                f'Variable "{name}" contains characters that conflict with '
                f'the specified delimiters: "{self.delimiters}"'
            )


        # Validate capture group names
        regex_pattern = pcre2.compile(regex)
        capture_group_names = set(regex_pattern.groupindex.keys())
        for capture_group_name in capture_group_names:
            if capture_group_name in self.variable_names:
                raise AttributeError(
                    f'Capture group name "{capture_group_name}" in variable "{name}" '
                    f'cannot coexist with another variable named "{capture_group_name}".'
                )
            if capture_group_name in self.capture_group_names:
                raise AttributeError(
                    f'Variable "{name}" defines a capture group "{capture_group_name}" that duplicates '
                    f'a group already present in variable "{self.capture_group_names[name].name}".'
                )
            if any(char in capture_group_name for char in self.decoded_delimiters):
                raise ValueError(
                    f'Capture group "{capture_group_name}" in variable "{name}" '
                    f'contains delimiter characters: "{self.delimiters}"'
                )

        log_surgeon_variable = LogSurgeonVariable(name, regex, capture_group_names)
        self.variables.append(log_surgeon_variable)
        self.variable_names[name] = log_surgeon_variable
        self.capture_group_names[name] = log_surgeon_variable

    def add_schema_timestamp(self, pattern: str):
        raise NotImplemented

    def compile_schema(self) -> str:
        schema_entries = [f"delimiters:{self.delimiters}"]
        for variable in self.variables:
            schema_entries.append(variable.get_schema_variable_entry())
        return "\n".join(schema_entries)

    def parse_string(self, payload: str):
        parser = ReaderParser(io.StringIO(payload), self.compile_schema())
        event = parser.parse_next_log_event()
        return event


if __name__ == '__main__':
    parser = LogSurgeonParser()

    # Begin with a basic motivating example: " INFO [main] MemoryStore: MemoryStore started with capacity 7.0 GiB\n"
    # 1. Extract the numeric value "7.0" from the log
    # 2. Assign it the label "MemoryStoreCapacityGiB"
    # 3. Generate log type (template)

    # We can achieve this easily using log surgeon
    # The first step is to specify the schema used for labeling, extraction and templating
    # We define a variable name, and a regular expression with a named capture group.
    parser.add_schema_variable("MemoryStore",
                               "MemoryStore started with capacity (?<MemoryStoreCapacityGiB>\d+\.\d+) GiB")

    # Before we parse anything, log-surgeon will jit-compile a model similar to re.compile
    event = parser.parse_string(" INFO [main] MemoryStore: MemoryStore started with capacity 7.0 GiB\n")

    # Log-surgeon identifies and labels and extracts the variables in unstructured text, no matter where it is,
    # and also generates
    print("#######################################################")
    print(f"Message: {event.get_log_message().strip()}")
    print(f"\t@LogType -> {event.get_log_type()}")
    print(f"\tMemoryStoreCapacityGiB -> {event['MemoryStoreCapacityGiB']}")

    # Let's iterate on this example log and extract 3 platform variables: level, thread, component
    parser = LogSurgeonParser()
    parser.add_schema_variable("MemoryStore",
                               "MemoryStore started with capacity (?<MemoryStoreCapacityGiB>\d+\.\d+) GiB")
    parser.add_schema_variable("Platform",
                               "(?<level>(INFO)|(WARN)|(ERROR)) \[(?<thread>.+)\] (?<component>.+):")
    event = parser.parse_string(" INFO [main] MemoryStore: MemoryStore started with capacity 7.0 GiB\n")
    print("#######################################################")
    print(f"Message: {event.get_log_message().strip()}")
    print(f"\t@LogType -> {event.get_log_type()}")
    print(f"\tlevel -> {event['level']}")
    print(f"\tthread -> {event['thread']}")
    print(f"\tcomponent -> {event['component']}")
    print(f"\tMemoryStoreCapacityGiB -> {event['MemoryStoreCapacityGiB']}")