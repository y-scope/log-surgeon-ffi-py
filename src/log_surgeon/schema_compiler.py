r"""
Schema compiler for constructing log-surgeon schema definitions.

This module provides the SchemaCompiler class, which builds schema definitions
used by the log-surgeon parsing engine. While most users will interact with
the higher-level Parser class, SchemaCompiler provides low-level control for
advanced use cases.

The compiled schema defines:
- Delimiters for tokenization
- Timestamp patterns for multi-line event detection
- Variable patterns with capture groups for extraction

Example
-------
```python
from log_surgeon.schema_compiler import SchemaCompiler

compiler = SchemaCompiler()
compiler.add_var("request", r"(?<method>GET|POST) (?<path>/\S+)")
compiler.add_var("status", r"status=(?<code>\d+)")
schema = compiler.compile()

# schema is a string ready for the log-surgeon engine
```

See Also
--------
Parser : High-level interface that uses SchemaCompiler internally.
"""

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

    SchemaCompiler provides a fluent interface for building schema definitions
    used by the log-surgeon parsing engine. It handles variable registration,
    pattern validation, and schema serialization.

    Key Responsibilities
    --------------------
    - Register variable patterns with named capture groups
    - Track capture group names for validation
    - Manage variable priority for pattern ordering
    - Generate hidden variable names for internal use
    - Compile the final schema string

    Schema Format
    -------------
    The compiled schema is a text format with sections for delimiters,
    timestamps, and variables:

    ```
    delimiters: \t\r\n:,!;%@/()[]
    timestamp:<pattern>
    VariableName:<pattern>
    ```

    Priority System
    ---------------
    Variables are ordered in the schema by:
    1. Priority (descending): higher priority = appears first
    2. Insertion order (ascending): earlier added = appears first

    This ordering affects which pattern is tried first when multiple
    patterns could match the same text.

    Note
    ----
    Most users should use the Parser class, which provides a simpler
    interface and handles schema compilation automatically. Use
    SchemaCompiler directly only for advanced use cases.

    Example
    -------
    ```python
    from log_surgeon.schema_compiler import SchemaCompiler

    compiler = SchemaCompiler()

    # Add patterns with priority
    compiler.add_var("ip", r"(?<ip>[0-9.]+)", priority=10)
    compiler.add_var("request", r"(?<method>GET|POST) (?<path>/\S+)")
    compiler.add_var("int", r"(?<num>\d+)", priority=-1)  # Low priority

    # Add timestamp for multi-line event detection
    compiler.add_timestamp("iso", r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")

    # Compile to schema string
    schema = compiler.compile()
    ```

    See Also
    --------
    Parser : High-level interface for log parsing.
    Variable : Data class representing a variable definition.
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
        r"""
        Add a timestamp pattern to the schema.

        Timestamps help log-surgeon detect log event boundaries. When a
        timestamp pattern matches at the start of a line, it signals a
        new log event, enabling correct handling of multi-line events
        like stack traces.

        Args:
            name: Unique identifier for this timestamp pattern.
            regex: Regular expression for matching timestamp formats.

        Returns:
            Self for method chaining.

        Example
        -------
        ```python
        compiler = SchemaCompiler()
        compiler.add_timestamp("iso", r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}")
        compiler.add_timestamp("unix", r"\d{10}")
        ```

        """
        self.timestamps[name] = regex
        return self

    def add_var(self, name: str, regex: str, priority: int = 0) -> "SchemaCompiler":
        r"""
        Add a variable pattern to the schema.

        Patterns must include at least one named capture group using
        `(?<name>...)` syntax. The capture group names become the keys
        for accessing extracted values from parsed events.

        Args:
            name: Unique identifier for this variable pattern.
            regex: Regular expression with named capture groups.
                Use `(?<name>pattern)` syntax for extraction.
            priority: Pattern ordering priority. Higher values are tried
                first during matching. Default is 0.

                - Use positive values for specific patterns (IP, UUID)
                - Use negative values for generic catch-alls (INT, FLOAT)

        Returns:
            Self for method chaining.

        Raises:
            ValueError: If pattern has no capture groups, or if names
                contain delimiter characters.
            AttributeError: If a variable with this name already exists.

        Example
        -------
        ```python
        compiler = SchemaCompiler()
        compiler.add_var("ip", r"(?<ip>[0-9.]+)", priority=10)
        compiler.add_var("request", r"(?<method>GET|POST) (?<path>/\S+)")
        compiler.add_var("int", r"(?<num>\d+)", priority=-1)
        ```

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
        Validate that a variable name does not conflict with existing names or delimiters.

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
        Compile the schema to a string for the log-surgeon engine.

        Generates the final schema definition that includes delimiters,
        timestamps, and variables ordered by priority. This string is
        passed to the log-surgeon C++ library for DFA compilation.

        Returns:
            Schema definition string in log-surgeon format.

        Note
        ----
        Variables are ordered by:
        1. Priority (descending): higher priority patterns first
        2. Insertion order (ascending): earlier added patterns first

        This ordering determines which pattern is tried first when multiple
        patterns could match the same text.

        Example
        -------
        ```python
        compiler = SchemaCompiler()
        compiler.add_var("ip", r"(?<ip>[0-9.]+)", priority=10)
        compiler.add_var("number", r"(?<num>\d+)", priority=-1)
        compiler.add_timestamp("ts", r"\d{4}-\d{2}-\d{2}")

        schema = compiler.compile()
        # Returns formatted schema string with sections for
        # delimiters, timestamps, and variables
        ```

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
