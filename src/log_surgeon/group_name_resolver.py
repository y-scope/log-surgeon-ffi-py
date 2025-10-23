"""Group name resolver for mapping between logical and physical capture group names."""

from collections.abc import KeysView


class GroupNameResolver:
    """
    Bidirectional mapping between logical (user-defined) and physical (auto-generated) group names.

    This resolver manages the mapping between human-readable logical names and
    auto-generated physical names used internally by log-surgeon. One logical name
    can map to multiple physical names (one-to-many), while each physical name maps
    to exactly one logical name (one-to-one in reverse).

    The resolver is used to:
    - Generate unique physical names for each capture group
    - Resolve physical names back to user-friendly logical names
    - Support multiple instances of the same logical capture group

    Example:
        >>> resolver = GroupNameResolver("CGPrefix")
        >>> phys1 = resolver.create_new_physical_name("user_id")  # "CGPrefix0"
        >>> phys2 = resolver.create_new_physical_name("user_id")  # "CGPrefix1"
        >>> resolver.get_logical_name(phys1)  # "user_id"
        >>> resolver.get_physical_names("user_id")  # {"CGPrefix0", "CGPrefix1"}

    """

    def __init__(self, physical_name_prefix: str) -> None:
        """
        Initialize the group name resolver.

        Args:
            physical_name_prefix: Prefix for auto-generated physical names
                (e.g., "CGPrefix" generates "CGPrefix0", "CGPrefix1", etc.)

        """
        # Forward mapping: logical name -> set of physical names (one-to-many)
        self._forward: dict[str, set[str]] = {}
        # Reverse mapping: physical name -> logical name (one-to-one)
        self._reverse: dict[str, str] = {}

        self._physical_name_prefix: str = physical_name_prefix
        self._next_physical_name_id: int = 0

    def create_new_physical_name(self, logical_name: str) -> str:
        """
        Create a new unique physical name for a logical name.

        Each call generates a new physical name, even if called multiple times
        with the same logical name. This allows the same logical capture group
        to appear multiple times in a schema.

        Args:
            logical_name: User-defined logical name for the capture group

        Returns:
            Auto-generated unique physical name

        Example:
            >>> resolver = GroupNameResolver("CGPrefix")
            >>> resolver.create_new_physical_name("user_id")
            'CGPrefix0'
            >>> resolver.create_new_physical_name("user_id")
            'CGPrefix1'
            >>> resolver.create_new_physical_name("thread")
            'CGPrefix2'

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
            Set of all physical names mapped to the logical name

        Raises:
            KeyError: If logical name has not been registered

        Example:
            >>> resolver = GroupNameResolver("CGPrefix")
            >>> resolver.create_new_physical_name("user_id")
            'CGPrefix0'
            >>> resolver.create_new_physical_name("user_id")
            'CGPrefix1'
            >>> resolver.get_physical_names("user_id")
            {'CGPrefix0', 'CGPrefix1'}

        """
        return self._forward[logical_name]

    def get_logical_name(self, physical_name: str) -> str:
        """
        Get the logical name for a physical name.

        Args:
            physical_name: Physical name to look up

        Returns:
            The logical name that was used to create the physical name

        Raises:
            KeyError: If physical name has not been registered

        Example:
            >>> resolver = GroupNameResolver("CGPrefix")
            >>> resolver.create_new_physical_name("user_id")
            'CGPrefix0'
            >>> resolver.get_logical_name("CGPrefix0")
            'user_id'

        """
        return self._reverse[physical_name]

    def get_all_logical_names(self) -> KeysView[str]:
        """
        Get all logical names that have been registered.

        Returns:
            A view of all logical names that have at least one physical name mapping

        Example:
            >>> resolver = GroupNameResolver("CGPrefix")
            >>> resolver.create_new_physical_name("user_id")
            'CGPrefix0'
            >>> resolver.create_new_physical_name("thread")
            'CGPrefix1'
            >>> resolver.get_all_logical_names()
            dict_keys(['user_id', 'thread'])

        """
        return self._forward.keys()
