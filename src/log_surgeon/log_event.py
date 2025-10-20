class LogEvent:
    """ """

    def __init__(self) -> None:
        self._log_message: str = ""
        self._var_dict: dict[str, str | list[str | int | float]] = {}

    def get_log_message(self) -> str:
        return self._log_message

    def get_variable(
        self, variable_name: str, raw_output: bool = False
    ) -> str | list[str | int | float]:
        val = self._var_dict[variable_name]
        return val if raw_output or len(val) != 1 else val[0]

    def get_log_type(self) -> str:
        return self._var_dict["@LogType"]

    def __getitem__(self, variable_name: str) -> str | list[str | int | float]:
        return self.get_variable(variable_name, raw_output=False)

    def __str__(self) -> str:
        return self.get_log_message()

    def __repr__(self) -> str:
        return self.get_log_message()
