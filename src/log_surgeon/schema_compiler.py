"""Schema compiler for constructing log-surgeon schema definitions."""

import re

from log_surgeon.variable import Variable

DEFAULT_DELIMITERS = r" \t\r\n:,!;%@/()[]"
"""Default delimiter characters for tokenization."""

LOG_SURGEON_HIDDEN_VARIABLE_PREFIX = "LogSurgeonHiddenVariables"
"""Prefix for auto-generated hidden variable names."""

_VARIABLE_EXISTS_ERROR = 'Variable "{name}" already exists and must be unique.'
_VARIABLE_DELIMITER_CONFLICT_ERROR = (
    'Variable "{name}" contains characters that conflict with '
    'the specified delimiters: "{delimiters}"'
)


class SchemaCompiler:
    r"""
    Compiler for constructing log-surgeon schema definitions.

    The SchemaCompiler provides a fluent interface for defining variables, timestamps,
    and delimiters that will be used to parse log messages.

    Example:
        >>> compiler = SchemaCompiler()
        >>> compiler.add_var("metric", r"value=(?<value>\\d+)")
        >>> compiler.add_timestamp("ts", r"\\d{4}/\\d{2}/\\d{2}")
        >>> schema = compiler.compile()

    """

    def __init__(self, delimiters: str = DEFAULT_DELIMITERS) -> None:
        """
        Initialize a schema compiler.

        Args:
            delimiters: String of delimiter characters for tokenization.
                Default includes space, tab, newline, and common punctuation.

        """
        self.delimiters: str = delimiters
        self.decoded_delimiters: str = delimiters.encode().decode("unicode_escape")

        # Maintain ordered list of Variables and quick lookup dictionary
        self.vars: list[Variable] = []
        self.var_names: dict[str, Variable] = {}
        self.var_hidden_names: dict[str, str] = {}
        self._var_hidden_name_id: int = 0
        self._var_insertion_order: int = 0

        self.timestamps: dict[str, str] = {}

        # Track all capture group names
        self._capture_group_names: set[str] = set()

    def add_timestamp(self, name: str, regex: str) -> "SchemaCompiler":
        """
        Add a timestamp pattern to the schema.

        Args:
            name: Name identifier for the timestamp
            regex: Regular expression pattern for matching timestamps

        Returns:
            Self for method chaining

        """
        self.timestamps[name] = regex
        return self

    def add_var(self, name: str, regex: str, priority: int = 0) -> "SchemaCompiler":
        """
        Add a variable pattern to the schema.

        Args:
            name: Variable name
            regex: Regular expression pattern (supports (?<name>) capture groups)
            priority: Priority for ordering in schema (higher = appears first).
                Default is 0. Use negative values for generic patterns (e.g., -1 for int/float).
                Variables with same priority maintain insertion order.

        Returns:
            Self for method chaining

        Raises:
            AttributeError: If variable name conflicts with existing names
            ValueError: If variable/capture names contain delimiter characters

        """
        # Extract capture group names
        converted_regex = regex.replace("(?<", "(?P<")
        capture_group_names = set(re.compile(converted_regex).groupindex.keys())
        if len(capture_group_names) < 1:
            msg = (
                f"Pattern requires at least one named capture group (e.g., (?<name>...). "
                f"Provided: {regex}"
            )
            raise ValueError(msg)

        # Track all capture group names
        self._capture_group_names.update(capture_group_names)

        # Generate hidden variable name with prefix that will be stripped from log-surgeon output
        hidden_name = f"{LOG_SURGEON_HIDDEN_VARIABLE_PREFIX}{self._var_hidden_name_id}"
        self._var_hidden_name_id += 1
        self.var_hidden_names[name] = hidden_name
        name = hidden_name

        # Validate variable name
        self._validate_variable_name(name)

        # Create and register variable
        var = Variable(name, regex, capture_group_names, priority, self._var_insertion_order)
        self._var_insertion_order += 1
        self.vars.append(var)
        self.var_names[name] = var

        return self

    def _validate_variable_name(self, name: str) -> None:
        """
        Validate that a variable name doesn't conflict with existing names or delimiters.

        Args:
            name: Variable name to validate

        Raises:
            AttributeError: If variable name already exists
            ValueError: If variable name contains delimiter characters

        """
        if name in self.var_names:
            raise AttributeError(_VARIABLE_EXISTS_ERROR.format(name=name))
        if any(char in name for char in self.decoded_delimiters):
            raise ValueError(
                _VARIABLE_DELIMITER_CONFLICT_ERROR.format(name=name, delimiters=self.delimiters)
            )

    def remove_var(self, var_name: str) -> "SchemaCompiler":
        """
        Remove a variable from the schema.

        Args:
            var_name: Name of the variable to remove (or its original name if hidden)

        Returns:
            Self for method chaining

        """
        # Resolve hidden name if applicable
        actual_name = self.var_hidden_names.get(var_name, var_name)

        var = self.var_names.pop(actual_name)
        self.vars.remove(var)

        return self

    def get_var(self, var_name: str) -> Variable:
        """
        Get a variable by name.

        Args:
            var_name: Variable name

        Returns:
            The Variable object

        """
        return self.var_names[var_name]

    def get_all_capture_group_names(self) -> set[str]:
        """
        Get all capture group names defined in the schema.

        Returns:
            Set of all capture group names

        """
        return self._capture_group_names

    def compile(self) -> str:
        r"""
        Compile the final schema string.

        Returns:
            Schema definition string ready for use with the parser

        Example:
            >>> compiler = SchemaCompiler()
            >>> compiler.add_var("MyVar", r"pattern (?<field>[a-zA-Z]+)")
            >>> schema = compiler.compile()

        """
        schema_sections = [f"// schema delimiters\ndelimiters:{self.delimiters}"]

        if self.timestamps:
            timestamp_entries = "\n".join(
                f"timestamp:{regex}" for regex in self.timestamps.values()
            )
            schema_sections.append(f"// schema timestamps\n{timestamp_entries}")

        if self.vars:
            # Sort by priority (descending), then by insertion order (ascending)
            sorted_vars = sorted(self.vars, key=lambda v: (-v.priority, v.insertion_order))
            var_entries = "\n".join(f"{var.name}:{var.regex}" for var in sorted_vars)
            schema_sections.append(f"// schema variables\n{var_entries}")

        return "\n\n".join(schema_sections)
