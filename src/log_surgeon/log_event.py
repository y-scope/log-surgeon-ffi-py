import json

class LogEvent:
    """ """

    def __init__(self) -> None:
        self._log_message: str = ""
        self._var_dict: dict[str, str | list[str | int | float]] = {}

    def get_log_message(self) -> str:
        return self._log_message


    def get_variable(self, variable_name: str, raw_output: bool = False) -> str | list[str | int | float] | None:
        val = self._var_dict.get(variable_name)

        if variable_name == "@LogType":
            return val

        if not val:  # Covers both None and empty list
            return None

        if raw_output or len(val) != 1:
            return val

        return val[0]

    def get_variable_str(self, variable_name: str) -> str | None:
        values = self._var_dict.get(variable_name)

        if not values:
            return None

        return ",".join(map(str, values))


    def get_log_type(self) -> str:
        return self._var_dict['@LogType']

    def __getitem__(self, variable_name: str) -> str | list[str | int | float]:
        return self.get_variable(variable_name, raw_output=False)

    def __str__(self) -> str:
        return json.dumps({key: self.get_variable(key) for key in self._var_dict}, indent=2)

    def __repr__(self) -> str:
        return json.dumps(self._var_dict)
