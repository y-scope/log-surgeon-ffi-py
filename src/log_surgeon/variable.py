"""Variable definition for log-surgeon schema."""


class Variable:
    """
    Represents a variable pattern in a log-surgeon schema.

    A Variable defines a named pattern that can be matched in log messages,
    with optional named capture groups for extracting specific fields.

    Attributes:
        name: Variable name
        regex: Regular expression pattern
        capture_group_names: Set of logical capture group names in the pattern

    """

    def __init__(self, name: str, regex: str, capture_group_names: set[str]) -> None:
        """
        Initialize a Variable.

        Args:
            name: Variable name
            regex: Regular expression pattern
            capture_group_names: Set of logical capture group names

        """
        self.name = name
        self.regex = regex
        self.capture_group_names = capture_group_names
