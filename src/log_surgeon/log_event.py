class LogEvent:
    """ """

    def __init__(self) -> None:
        self._log_message: str = ""
        self._var_dict: dict[str, str | list[str | int | float]] = {}

    def get_log_message(self) -> str:
        return self._log_message

    def __getitem__(self, variable_name: str) -> str | list[str | int | float]:
        val = self._var_dict[variable_name]
        return val[0] if len(val) == 1 else val

    def __str__(self) -> str:
        return self.get_log_message()

    def __repr__(self) -> str:
        return self.get_log_message()
