from typing import List

import re

from log_surgeon.variable import Variable

DEFAULT_DELIMITERS = " \t\r\n:,!;%@/\(\)\[\]"
LOG_SURGEON_HIDDEN_VARIABLE_PREFIX = "LogSurgeonHiddenVariables"

class SchemaBuilder:
    def __init__(self, delimiters: str = DEFAULT_DELIMITERS) -> None:
        self.delimiters = delimiters
        self.decoded_delimiters = delimiters.encode().decode('unicode_escape')

        self.vars: List[Variable] = []
        self.var_names: dict[str, Variable] = {}
        self.var_hidden_names: dict[str, str] = {}
        self.var_hidden_name_id = 0
        self.capture_group_names: dict[str, Variable] = {}
        self.timestamps: dict[str, str] = {}

    def add_timestamp(self, name: str, regex: str):
        self.timestamps[name] = regex

    def add_var(self, name: str, regex: str, hide_var_name_if_named_group_present: bool = True):
        # Validate capture group names
        converted_regex = regex.replace("(?<", "(?P<")
        capture_group_names = set(re.compile(converted_regex).groupindex.keys())

        if hide_var_name_if_named_group_present and len(capture_group_names) > 0:
            # Want to create a random name with static prefix that we want to ignore later
            # This should create random names that we can hide later
            hidden_name = f"{LOG_SURGEON_HIDDEN_VARIABLE_PREFIX}{self.var_hidden_name_id}"
            self.var_hidden_name_id += 1
            self.var_hidden_names[name] = hidden_name
            name = hidden_name

        # Validate variable name
        if name in self.var_names:
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
        for capture_group_name in capture_group_names:
            if capture_group_name in self.var_names:
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

        var = Variable(name, regex, capture_group_names)
        self.vars.append(var)
        self.var_names[name] = var
        self.capture_group_names[name] = var

        return self

    def remove_var(self, var_name: str):
        # Resolve hidden name using mapping if available
        hidden_name = self.var_hidden_names.get(var_name)
        if hidden_name is not None:
            var_name = hidden_name

        var = self.var_names.pop(var_name)
        self.vars.remove(var)
        for capture_group_name in var.capture_group_names:
            del self.capture_group_names[capture_group_name]

        return self

    def get_var(self, var_name: str) -> Variable:
        return self.var_names[var_name]

    def get_var_from_capture_group_name(self, capture_group_name: str) -> Variable:
        return self.capture_group_names[capture_group_name]

    def build(self) -> str:
        # Schema delimiters
        schema_sections = [f"// schema delimiters\ndelimiters:{self.delimiters}"]

        # Timestamp entries
        if self.timestamps:
            timestamp_entries = "\n".join(f"timestamp:{regex}" for regex in self.timestamps.values())
            schema_sections.append(f"// schema timestamps\n{timestamp_entries}")

        # Variable entries
        if self.vars:
            var_entries = "\n".join(f"{var.name}:{var.regex}" for var in self.vars)
            schema_sections.append(f"// schema variables\n{var_entries}")

        return "\n\n".join(schema_sections)
