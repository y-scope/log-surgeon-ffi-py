import json
import re

from log_surgeon.group_name_resolver import GroupNameResolver


class LogEvent:
    """
    Represents a parsed log event with extracted variables and metadata.

    A LogEvent contains the original log message, a log type (template), and
    extracted variables from the log message based on the schema pattern.
    """

    def __init__(self) -> None:
        """Initialize an empty LogEvent."""
        self._log_message: str = ""
        self._var_dict: dict[str, str | list[str | int | float]] = {}
        self._group_name_resolver: GroupNameResolver | None = None

    def get_log_message(self) -> str:
        """
        Get the original log message.

        Returns:
            The raw log message string
        """
        return self._log_message

    def get_log_type(self) -> str:
        """
        Get the log type (template) for this event with resolved group names.

        Returns:
            The log type string with placeholders for variable fields,
            prefixed with <timestamp> and with logical group names resolved
        """
        def resolve_physical_group_name(match):
            physical_group_name = match.group(1)
            logical_group_name = self._group_name_resolver.get_logical_name(physical_group_name)
            return f"<{logical_group_name}>"

        resolved_logtype = re.sub(
            r"<(CGPrefix\d+)>",
            resolve_physical_group_name,
            self._var_dict['@LogType']
        )
        return f"<timestamp>{resolved_logtype}"

    def get_capture_group(
        self,
        logical_capture_group_name: str,
        raw_output: bool = False
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
            >>> event.get_capture_group('thread', resolver)  # Single value
            'main'
            >>> event.get_capture_group('thread', resolver, raw_output=True)
            ['main']
            >>> event.get_capture_group('errors', resolver)  # Multiple values
            ['error1', 'error2']
        """
        # Special case: @LogType returns the resolved log type
        if logical_capture_group_name == "@LogType":
            return self.get_log_type()

        # Look up all physical names for this logical name
        for physical_group_name in self._group_name_resolver.get_physical_names(logical_capture_group_name):
            value = self._var_dict.get(physical_group_name)
            if value:
                if raw_output or len(value) > 1:
                    return value
                return value[0]

        return None

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
        resolved_dict = {}
        for key, value in self._var_dict.items():
            if key == "@LogType":
                continue
            logical_name = self._group_name_resolver.get_logical_name(key)
            if value:
                if len(value) > 1:
                    resolved_dict[logical_name] = value
                else:
                    resolved_dict[logical_name] = value[0]

        return json.dumps(resolved_dict, indent=2)

    def __repr__(self) -> str:
        """
        Get a compact JSON representation of the internal variable dictionary.

        Returns:
            Compact JSON string of the variable dictionary
        """
        return json.dumps(self._var_dict)
