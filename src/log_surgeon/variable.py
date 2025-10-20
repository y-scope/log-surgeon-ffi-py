class Variable:
    def __init__(self, name: str, regex: str, capture_group_names: set[str]) -> None:
        self.name = name
        self.regex = regex
        self.capture_group_names = capture_group_names
