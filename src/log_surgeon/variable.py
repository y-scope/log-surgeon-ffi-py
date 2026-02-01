"""
Variable definition for log-surgeon schema.

This module provides the Variable class, which represents a single pattern
definition in a log-surgeon schema. Variables are created and managed by
SchemaCompiler.

Note
----
This is an internal class. Users should interact with patterns through
the Parser.add_var() method rather than creating Variable instances directly.
"""


class Variable:
    r"""
    Represents a variable pattern in a log-surgeon schema.

    A Variable defines a named pattern that can be matched in log messages.
    Each variable has named capture groups that define what values to extract.

    This is an internal class used by SchemaCompiler. Users should use
    Parser.add_var() instead of creating Variable instances directly.

    Attributes
    ----------
    name : str
        Internal variable name (may be auto-generated with a hidden prefix).
    regex : str
        Regular expression pattern with named capture groups.
    capture_group_names : set[str]
        Names of all capture groups defined in the pattern.
    priority : int
        Priority for schema ordering. Higher values appear first and are
        matched before lower priority patterns.
    insertion_order : int
        Order in which the variable was added. Used as a tiebreaker when
        priorities are equal, ensuring stable ordering.

    Example
    -------
    ```python
    # Internal usage by SchemaCompiler
    var = Variable(
        name="HiddenVar0",
        regex=r"(?<method>GET|POST) (?<path>/\S+)",
        capture_group_names={"method", "path"},
        priority=0,
        insertion_order=0,
    )
    ```

    See Also
    --------
    SchemaCompiler : Creates and manages Variable instances.
    Parser.add_var : User-facing method for adding patterns.
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
            name: Internal variable name for the schema.
            regex: Regular expression pattern with named capture groups.
            capture_group_names: Set of all capture group names in the pattern.
            priority: Pattern matching priority (higher = tried first).
            insertion_order: Order added (for stable sorting of equal priorities).

        """
        self.name = name
        self.regex = regex
        self.capture_group_names = capture_group_names
        self.priority = priority
        self.insertion_order = insertion_order
