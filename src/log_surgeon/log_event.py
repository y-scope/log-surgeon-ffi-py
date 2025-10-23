"""Log event representation with extracted variables and metadata."""

from __future__ import annotations

import json
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from log_surgeon.group_name_resolver import GroupNameResolver


class LogEvent:
    """
    Represents a parsed log event with extracted variables and metadata.

    A LogEvent contains the original log message, a log type (template), and
    extracted variables from the log message based on the schema pattern matching.
    Variables can be accessed directly using dictionary-style indexing with their
    logical (user-defined) names.

    Example:
        >>> event = parser.parse_event("INFO [main] Processing value=42")
        >>> event.get_log_message()
        'INFO [main] Processing value=42'
        >>> event["value"]
        '42'
        >>> event.get_log_type()
        '<timestamp><platform_level> [<platform_thread>] Processing value=<value>'

    """

    def __init__(self) -> None:
        """Initialize an empty LogEvent."""
        self._log_message: str | None = None
        self._var_dict: dict[str, str | list[str | int | float]] = {}
        self._group_name_resolver: GroupNameResolver | None = None

    def get_log_message(self) -> str:
        """
        Get the original log message.

        Returns:
            The raw log message string

        """
        assert self._log_message is not None, "LogEvent._log_message not initialized by FFI layer"
        return self._log_message

    def get_log_type(self) -> str:
        """
        Get the log type (template) for this event with resolved group names.

        Returns:
            The log type string with placeholders for variable fields,
            prefixed with <timestamp> and with logical group names resolved

        """

        def resolve_physical_group_name(match: re.Match[str]) -> str:
            physical_group_name = match.group(1)
            # _group_name_resolver is always initialized by FFI layer
            logical_group_name = self._group_name_resolver.get_logical_name(physical_group_name)  # type: ignore[union-attr]
            return f"<{logical_group_name}>"

        log_type_value = self._var_dict.get("@LogType")
        if not isinstance(log_type_value, str):
            msg = "LogType not found or invalid in LogEvent"
            raise TypeError(msg)

        resolved_logtype = re.sub(r"<(CGPrefix\d+)>", resolve_physical_group_name, log_type_value)
        return f"{resolved_logtype}"

    def get_capture_group(
        self, logical_capture_group_name: str, raw_output: bool = False
    ) -> str | list[str | int | float] | None:
        """
        Get the value of a capture group by its logical name.

        Args:
            logical_capture_group_name: Logical (user-defined) name of the capture group
            raw_output: If True, always return the raw list. If False (default),
                return unwrapped value for single-element lists

        Returns:
            - For @LogType: the resolved log type string
            - For capture groups with no values: None
            - For capture groups with single value (raw_output=False): the unwrapped value
            - Otherwise: list of values

        Example:
            >>> event.get_capture_group("thread", resolver)  # Single value
            'main'
            >>> event.get_capture_group("thread", resolver, raw_output=True)
            ['main']
            >>> event.get_capture_group("errors", resolver)  # Multiple values
            ['error1', 'error2']

        """
        # Special case: @LogType returns the resolved log type
        if logical_capture_group_name == "@log_type":
            return self.get_log_type()

        if logical_capture_group_name == "@log_message":
            return self.get_log_message()

        # Look up all physical names for this logical name
        # _group_name_resolver is always initialized by FFI layer
        physical_names = self._group_name_resolver.get_physical_names(  # type: ignore[union-attr]
            logical_capture_group_name
        )
        for physical_group_name in physical_names:
            value = self._var_dict.get(physical_group_name)
            if value:
                if raw_output or len(value) > 1:
                    return value
                return value[0]  # type: ignore[return-value]

        return None

    def get_capture_group_str_representation(
        self, logical_capture_group_name: str, raw_output: bool = False
    ) -> str:
        """
        Get the string representation of a capture group value.

        Args:
            logical_capture_group_name: Logical name of the capture group
            raw_output: If True, return raw list format. If False, unwrap single values

        Returns:
            String representation of the capture group value

        Example:
            >>> event.get_capture_group_str_representation("value")
            '42'
            >>> event.get_capture_group_str_representation("values", raw_output=True)
            "['1', '2', '3']"

        """
        return f"{self.get_capture_group(logical_capture_group_name, raw_output)}"

    def __getitem__(self, logical_capture_group_name: str) -> str | list[str | int | float]:
        """
        Access a capture group value by its logical name.

        Args:
            logical_capture_group_name: Logical (user-defined) name of the capture group

        Returns:
            The captured value(s) for the group

        Example:
            >>> event["thread"]
            'main'
            >>> event["values"]
            ['1', '2', '3']

        """
        result = self.get_capture_group(logical_capture_group_name, raw_output=False)
        if result is None:
            msg = f"Capture group '{logical_capture_group_name}' not found"
            raise KeyError(msg)
        return result

    def get_resolved_dict(self) -> dict[str, str | list[str | int | float]]:
        """
        Get a dictionary with all capture groups using logical (user-defined) names.

        This method converts the internal representation (which uses physical names like
        "CGPrefix0") to a user-friendly dictionary with logical names. Single-element
        lists are unwrapped to their scalar values.

        Returns:
            Dictionary mapping logical capture group names to their values.
            - "@LogType" is excluded from the output
            - Timestamp fields are consolidated under "timestamp" key
            - Physical names (CGPrefix*) are converted to logical names
            - Single-value lists are unwrapped to scalar values

        Example:
            >>> event.get_resolved_dict()
            {
                "timestamp": "2024-01-01T10:00:00",
                "level": "INFO",
                "thread": "main",
                "value": "42"
            }

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

            # _group_name_resolver is always initialized by FFI layer
            logical_name = self._group_name_resolver.get_logical_name(key)  # type: ignore[union-attr]
            if value:
                if len(value) > 1:
                    resolved_dict[logical_name] = value
                else:
                    resolved_dict[logical_name] = value[0]  # type: ignore[assignment]

        return resolved_dict

    def __str__(self) -> str:
        """
        Get a formatted JSON representation of the log event.

        Returns:
            Pretty-printed JSON string with all variables

        Example:
            >>> print(event)
            {
              "@LogType": "...",
              "field1": "value1"
            }

        """
        return json.dumps(self.get_resolved_dict(), indent=2)

    def __repr__(self) -> str:
        """
        Get a compact JSON representation of the internal variable dictionary.

        Returns:
            Compact JSON string of the variable dictionary

        """
        return json.dumps(self._var_dict)
