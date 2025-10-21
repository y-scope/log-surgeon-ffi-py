class GroupNameResolver:
    """
    Bidirectional mapping between logical (user-defined) and physical (auto-generated) group names.

    This resolver manages the mapping between human-readable logical names and
    auto-generated physical names used internally by log-surgeon. One logical name
    can map to multiple physical names.
    """

    def __init__(self, physical_name_prefix: str) -> None:
        """
        Initialize the group name resolver.

        Args:
            physical_name_prefix: Prefix for auto-generated physical names
        """
        # Forward: logical name -> set of physical names (one-to-many)
        self._forward: dict[str, set[str]] = {}
        # Reverse: physical name -> logical name (one-to-one)
        self._reverse: dict[str, str] = {}

        self._physical_name_prefix: str = physical_name_prefix
        self._next_physical_name_id: int = 0

    def create_new_physical_name(self, logical_name: str) -> str:
        """
        Create a new physical name for a logical name.

        A single logical name can have multiple physical names associated with it.

        Args:
            logical_name: User-defined logical name

        Returns:
            Auto-generated physical name

        Example:
            >>> resolver = GroupNameResolver("CGPrefix")
            >>> resolver.create_new_physical_name("user_id")
            '_phys_0'
            >>> resolver.create_new_physical_name("user_id")
            '_phys_1'
        """
        new_physical_name = f"{self._physical_name_prefix}{self._next_physical_name_id}"
        self._next_physical_name_id += 1

        # Add to forward mapping (logical -> physical)
        if logical_name not in self._forward:
            self._forward[logical_name] = {new_physical_name}
        else:
            self._forward[logical_name].add(new_physical_name)

        # Add to reverse mapping (physical -> logical)
        self._reverse[new_physical_name] = logical_name

        return new_physical_name

    def get_physical_names(self, logical_name: str) -> set[str]:
        """
        Get all physical names associated with a logical name.

        Args:
            logical_name: Logical name to look up

        Returns:
            Set of physical names for the logical name

        Raises:
            KeyError: If logical name not found
        """
        return self._forward[logical_name]

    def get_logical_name(self, physical_name: str) -> str:
        """
        Get the logical name for a physical name.

        Args:
            physical_name: Physical name to look up

        Returns:
            Logical name for the physical name

        Raises:
            KeyError: If physical name not found
        """
        return self._reverse[physical_name]

