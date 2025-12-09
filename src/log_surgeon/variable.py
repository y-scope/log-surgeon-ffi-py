"""Variable definition for log-surgeon schema."""


class Variable:
    """
    Represents a variable pattern in a log-surgeon schema.

    A Variable defines a named pattern that can be matched in log messages,
    with optional named capture groups for extracting specific fields.

    Attributes:
        name: Variable name
        regex: Regular expression pattern
        capture_group_names: Set of capture group names in the pattern
        priority: Priority for ordering in schema (higher = appears first)
        insertion_order: Order in which variable was added (for stable sorting)

    """

    def __init__(
        self,
        name: str,
        regex: str,
        capture_group_names: set[str],
        priority: int,
        insertion_order: int,
    ) -> None:
        """
        Initialize a Variable.

        Args:
            name: Variable name
            regex: Regular expression pattern
            capture_group_names: Set of capture group names
            priority: Priority for ordering (higher = appears first in schema)
            insertion_order: Order in which variable was added

        """
        self.name = name
        self.regex = regex
        self.capture_group_names = capture_group_names
        self.priority = priority
        self.insertion_order = insertion_order
