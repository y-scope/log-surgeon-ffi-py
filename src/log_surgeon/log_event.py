import json


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

    def get_log_message(self) -> str:
        """
        Get the original log message.

        Returns:
            The raw log message string
        """
        return self._log_message

    def get_log_type(self) -> str:
        """
        Get the log type (template) for this event.

        Returns:
            The log type string with placeholders for variable fields
        """
        return self._var_dict['@LogType']

    def get_variable(
        self,
        variable_name: str,
        raw_output: bool = False
    ) -> str | list[str | int | float] | None:
        """
        Get the value of a variable extracted from the log event.

        Args:
            variable_name: Name of the variable to retrieve
            raw_output: If True, always return the raw list. If False (default),
                return unwrapped value for single-element lists

        Returns:
            - For @LogType: the log type string
            - For variables with no values: None
            - For variables with single value (raw_output=False): the unwrapped value
            - Otherwise: list of values

        Example:
            >>> event['thread']  # Single value
            'main'
            >>> event.get_variable('thread', raw_output=True)
            ['main']
            >>> event['errors']  # Multiple values
            ['error1', 'error2']
        """
        val = self._var_dict.get(variable_name)

        # @LogType is always a string, not a list
        if variable_name == "@LogType":
            return val

        if not val:  # Covers both None and empty list
            return None

        if raw_output or len(val) != 1:
            return val

        return val[0]

    def get_variable_str(self, variable_name: str) -> str | None:
        """
        Get the value of a variable as a comma-separated string.

        Args:
            variable_name: Name of the variable to retrieve

        Returns:
            Comma-separated string of all values, or None if variable doesn't exist

        Example:
            >>> event.get_variable_str('ids')  # ids = [1, 2, 3]
            '1,2,3'
        """
        values = self._var_dict.get(variable_name)

        if not values:
            return None

        return ",".join(map(str, values))

    def __getitem__(self, variable_name: str) -> str | list[str | int | float] | None:
        """
        Get a variable value using dictionary-style access.

        Args:
            variable_name: Name of the variable

        Returns:
            Variable value (unwrapped if single value)

        Example:
            >>> event['field_name']
        """
        return self.get_variable(variable_name, raw_output=False)

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
        return json.dumps(
            {key: self.get_variable(key) for key in self._var_dict},
            indent=2
        )

    def __repr__(self) -> str:
        """
        Get a compact JSON representation of the internal variable dictionary.

        Returns:
            Compact JSON string of the variable dictionary
        """
        return json.dumps(self._var_dict)
