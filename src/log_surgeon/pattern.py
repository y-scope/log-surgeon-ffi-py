"""Common regex patterns for log parsing."""


class Pattern:
    """Collection of common regex patterns for log parsing."""

    UUID = r"[0-9a-fA-F]{8}\-[0-9a-fA-F]{4}\-[0-9a-fA-F]{4}\-[0-9a-fA-F]{4}\-[0-9a-fA-F]{12}"
    """Pattern for UUID (Universally Unique Identifier) strings."""

    IP_OCTET = "(25[0-5])|(2[0-4][0-9])|(1[0-9]{2})|([1-9]{0,1}[0-9])"
    """Pattern for a single IPv4 octet (0-255)."""

    IPV4 = f"(({IP_OCTET})\.){{3}}{IP_OCTET}"
    """Pattern for IPv4 addresses."""

    INT = r"\-{0,1}[0-9]+"
    """Pattern for integer numbers (with optional negative sign)."""

    FLOAT = rf"\-{{0,1}}[0-9]+\.[0-9]+"
    """Pattern for floating-point numbers (with optional negative sign)."""
