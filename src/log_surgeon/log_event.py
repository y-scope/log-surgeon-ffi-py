r"""
Log event representation with extracted variables and metadata.

This module provides the LogEvent class, which represents a parsed log message
with extracted variables. LogEvent objects are returned by Parser.parse() and
Parser.parse_event().

LogEvent provides dictionary-style access to extracted variables, making it
easy to work with parsed log data.

Example
-------
```python
from log_surgeon import Parser

parser = Parser()
parser.add_var("request", r"(?<method>GET|POST) (?<path>/\S+)")
parser.compile()

event = parser.parse_event("GET /api/users")

# Dictionary-style access
print(event["method"])  # "GET"
print(event["path"])    # "/api/users"

# Metadata access
print(event.get_log_message())  # "GET /api/users"
print(event.get_log_type())     # "<method> <path>"
```

See Also
--------
Parser : For creating and using parsers.
"""

from __future__ import annotations

import json


class LogEvent:
    r"""
    Represents a parsed log event with extracted variables and metadata.

    LogEvent is the result of parsing a log message with Parser. It contains:

    - The original log message
    - A log type (template with placeholders for matched variables)
    - Extracted variables accessible via dictionary-style indexing

    Accessing Variables
    -------------------
    Variables are accessed using dictionary-style indexing with the capture
    group name defined in your patterns:

    ```python
    event["field_name"]  # Returns the captured value
    ```

    For patterns that match multiple times, the value is a list. For single
    matches, the value is unwrapped to a scalar.

    Log Types
    ---------
    Log types are template strings where matched portions are replaced with
    placeholder names (e.g., "user=<user_id>"). They are useful for:

    - Log clustering and deduplication
    - Pattern frequency analysis
    - Anomaly detection (new log types indicate new behavior)

    Attributes
    ----------
    Note: These are internal attributes. Use the public methods to access data.

    _log_message : str
        The original log message text.
    _var_dict : dict
        Internal dictionary mapping capture group names to values.

    Example
    -------
    ```python
    parser = Parser()
    parser.add_var("request", r"(?<method>GET|POST) (?<path>/\S+) (?<code>\d+)")
    parser.compile()

    event = parser.parse_event("GET /api/users 200")

    # Access extracted variables
    print(event["method"])  # "GET"
    print(event["path"])    # "/api/users"
    print(event["code"])    # "200"

    # Access metadata
    print(event.get_log_message())  # "GET /api/users 200"
    print(event.get_log_type())     # "<method> <path> <code>"

    # Get all variables as a dictionary
    print(event.get_resolved_dict())
    # {"method": "GET", "path": "/api/users", "code": "200"}
    ```

    See Also
    --------
    Parser.parse : Parse multiple events from a source.
    Parser.parse_event : Parse a single event from a string.
    """

    def __init__(self) -> None:
        """Initialize an empty LogEvent."""
        self._log_message: str | None = None
        self._var_dict: dict[str, str | list[str | int | float]] = {}

    def get_log_message(self) -> str:
        """
        Get the original log message text.

        Returns the unmodified log message as it was parsed, including any
        whitespace, newlines, or special characters.

        Returns:
            The complete original log message string.

        Example
        -------
        ```python
        event = parser.parse_event("2024-01-01 INFO Processing complete")
        print(event.get_log_message())
        # "2024-01-01 INFO Processing complete"
        ```

        """
        assert self._log_message is not None, "LogEvent._log_message not initialized by FFI layer"
        return self._log_message

    def get_log_type(self) -> str:
        r"""
        Get the log type (template) for this event.

        The log type is the original message with matched variables replaced
        by placeholder names in angle brackets (e.g., `<variable_name>`).
        This creates a template that represents the message's structure.

        Returns:
            Template string with placeholders for extracted variables.

        Raises:
            TypeError: If log type is not available (internal error).

        Note
        ----
        Log types are useful for:

        - **Clustering**: Group similar log messages together
        - **Frequency analysis**: Count occurrences of each pattern
        - **Anomaly detection**: New log types may indicate unusual behavior

        Example
        -------
        ```python
        parser = Parser()
        parser.add_var("req", r"(?<method>GET|POST) (?<path>/\S+) (?<code>\d+)")
        parser.compile()

        # Same pattern, different values
        e1 = parser.parse_event("GET /users 200")
        e2 = parser.parse_event("POST /login 401")

        print(e1.get_log_type())  # "<method> <path> <code>"
        print(e2.get_log_type())  # "<method> <path> <code>"

        # Both have the same log type despite different values
        assert e1.get_log_type() == e2.get_log_type()
        ```

        """
        log_type_value = self._var_dict.get("@LogType")
        if not isinstance(log_type_value, str):
            msg = "LogType not found or invalid in LogEvent"
            raise TypeError(msg)

        return log_type_value

    def get_capture_group(
        self, name: str, raw_output: bool = False
    ) -> str | list[str | int | float] | None:
        r"""
        Get the value of a capture group by name.

        Retrieves the extracted value(s) for a named capture group. By default,
        single values are unwrapped from their list container for convenience.

        Args:
            name: Name of the capture group to retrieve. Special names:

                - `"@log_type"`: Returns the log type template
                - `"@log_message"`: Returns the original log message

            raw_output: If True, always return values as a list, even for
                single matches. If False (default), single-element lists are
                unwrapped to scalar values.

        Returns:
            The captured value(s):

            - `None` if the capture group wasn't matched
            - `str` for single values (when `raw_output=False`)
            - `list` for multiple values or when `raw_output=True`

        Note
        ----
        Use `raw_output=True` when you need consistent list handling, such as
        when iterating over potentially multi-value captures.

        Example
        -------
        ```python
        # Pattern that matches multiple times
        parser.add_var("errors", r"error: (?<error>\w+)")
        event = parser.parse_event("error: timeout error: disconnect")

        # Default: single values unwrapped, multiple values as list
        event.get_capture_group("error")  # ["timeout", "disconnect"]

        # With raw_output: always a list
        event.get_capture_group("error", raw_output=True)  # ["timeout", "disconnect"]

        # Single match example
        event2 = parser.parse_event("error: timeout")
        event2.get_capture_group("error")  # "timeout" (unwrapped)
        event2.get_capture_group("error", raw_output=True)  # ["timeout"]

        # Special names
        event.get_capture_group("@log_type")    # "<error> <error>"
        event.get_capture_group("@log_message") # "error: timeout error: disconnect"
        ```

        """
        # Special case: @LogType returns the log type
        if name == "@log_type":
            return self.get_log_type()

        if name == "@log_message":
            return self.get_log_message()

        # Look up the capture group value directly
        value = self._var_dict.get(name)
        if value:
            if raw_output or len(value) > 1:
                return value
            return value[0]  # type: ignore[return-value]

        return None

    def get_capture_group_str_representation(self, name: str, raw_output: bool = False) -> str:
        """
        Get the string representation of a capture group value.

        Args:
            name: Name of the capture group
            raw_output: If True, return raw list format. If False, unwrap single values

        Returns:
            String representation of the capture group value

        Example:
            ```python
            event.get_capture_group_str_representation("value")  # '42'
            event.get_capture_group_str_representation("values", raw_output=True)  # "['1', '2', '3']"
            ```

        """
        return f"{self.get_capture_group(name, raw_output)}"

    def __getitem__(self, name: str) -> str | list[str | int | float]:
        r"""
        Access a capture group value using dictionary-style indexing.

        This is the primary way to access extracted variables from a LogEvent.
        Single values are automatically unwrapped from lists for convenience.

        Args:
            name: Name of the capture group as defined in the pattern's
                `(?<name>...)` syntax.

        Returns:
            The captured value(s). Returns a scalar for single matches,
            or a list for multiple matches of the same capture group.

        Raises:
            KeyError: If the capture group name does not exist or was not matched.

        Example
        -------
        ```python
        parser = Parser()
        parser.add_var("request", r"(?<method>GET|POST) (?<path>/\S+)")
        parser.compile()

        event = parser.parse_event("GET /api/users")

        # Access like a dictionary
        print(event["method"])  # "GET"
        print(event["path"])    # "/api/users"

        # KeyError for missing fields
        try:
            event["nonexistent"]
        except KeyError as e:
            print(e)  # "Capture group 'nonexistent' not found"
        ```

        """
        result = self.get_capture_group(name, raw_output=False)
        if result is None:
            msg = f"Capture group '{name}' not found"
            raise KeyError(msg)
        return result

    def get_resolved_dict(self) -> dict[str, str | list[str | int | float]]:
        r"""
        Get all extracted variables as a dictionary.

        Returns a clean dictionary of all capture groups with their values.
        Single-element lists are unwrapped to scalar values for convenience.
        Internal fields like "@LogType" are excluded.

        Returns:
            Dictionary mapping capture group names to their extracted values.

            Processing applied:

            - `@LogType` is excluded (use `get_log_type()` instead)
            - Timestamp variants are consolidated under `"timestamp"` key
            - Single-value lists are unwrapped to scalar values
            - Multi-value captures remain as lists

        Note
        ----
        This method is useful for:

        - Converting log events to JSON or other formats
        - Passing extracted data to downstream processing
        - Debugging to see all extracted values at once

        Example
        -------
        ```python
        parser = Parser()
        parser.add_var("request", r"(?<method>GET|POST) (?<path>/\S+)")
        parser.add_var("status", r"status=(?<code>\d+)")
        parser.compile()

        event = parser.parse_event("GET /api/users status=200")
        result = event.get_resolved_dict()

        print(result)
        # {
        #     "method": "GET",
        #     "path": "/api/users",
        #     "code": "200"
        # }

        # Can be easily serialized
        import json
        print(json.dumps(result))
        ```

        """
        resolved_dict: dict[str, str | list[str | int | float]] = {}
        for key, value in self._var_dict.items():
            if key == "@LogType":
                continue
            if key in ["firstTimestamp", "timestamp", "newLineTimestamp"]:
                if len(value) > 1:
                    resolved_dict["timestamp"] = value
                else:
                    resolved_dict["timestamp"] = value[0]  # type: ignore[assignment]
                continue

            if value:
                if len(value) > 1:
                    resolved_dict[key] = value
                else:
                    resolved_dict[key] = value[0]  # type: ignore[assignment]

        return resolved_dict

    def __str__(self) -> str:
        """
        Get a formatted JSON representation of the log event.

        Returns:
            Pretty-printed JSON string with all variables

        Example:
            ```python
            print(event)
            # {
            #   "@LogType": "...",
            #   "field1": "value1"
            # }
            ```

        """
        return json.dumps(self.get_resolved_dict(), indent=2)

    def __repr__(self) -> str:
        """
        Get a compact JSON representation of the internal variable dictionary.

        Returns:
            Compact JSON string of the variable dictionary

        """
        return json.dumps(self._var_dict)
