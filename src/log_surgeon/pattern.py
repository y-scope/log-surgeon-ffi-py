"""Common regex patterns for log parsing."""


class PATTERN:
    """
    Collection of common regex patterns for log parsing.

    These patterns are designed for use with log-surgeon and follow log-surgeon's
    pattern syntax requirements (e.g., using (a)|(b) for alternation, {0,1} for optional).

    Example:
        >>> from log_surgeon import Parser, PATTERN
        >>> parser = Parser()
        >>> parser.add_var("ip", rf"IP: (?<ip>{PATTERN.IPV4})")
        >>> parser.add_var("port", rf"port (?<port>{PATTERN.PORT})")
        >>> parser.compile()

    """

    # ============================================================================
    # Network Patterns
    # ============================================================================

    UUID = r"[0-9a-fA-F]{8}\-[0-9a-fA-F]{4}\-[0-9a-fA-F]{4}\-[0-9a-fA-F]{4}\-[0-9a-fA-F]{12}"
    """
    Pattern for UUID (Universally Unique Identifier) strings.

    Matches standard UUID format with hyphens (8-4-4-4-12 hex digits).
    Example: "550e8400-e29b-41d4-a716-446655440000"
    """

    IP_OCTET = r"(25[0-5])|(2[0-4][0-9])|(1[0-9]{2})|([1-9]{0,1}[0-9])"
    """
    Pattern for a single IPv4 octet (0-255).

    Matches valid IPv4 octet values:
    - 250-255: (25[0-5])
    - 200-249: (2[0-4][0-9])
    - 100-199: (1[0-9]{2})
    - 0-99: ([1-9]{0,1}[0-9])

    Note: Uses log-surgeon alternation syntax with parentheses around each alternative.
    """

    IPV4 = rf"(({IP_OCTET})\.){{3}}{IP_OCTET}"
    """
    Pattern for IPv4 addresses.

    Matches standard dotted-decimal notation (e.g., "192.168.1.1").
    Composed of 3 octets followed by dots, then a final octet.

    Note: Uses {{3}} (escaped braces) for repetition in f-string.
    """

    PORT = r"\d{1,5}"
    """
    Pattern for network port numbers.

    Matches 1-5 digit port numbers (0-65535 range, though doesn't validate upper bound).
    Example: "80", "8080", "65535"
    """

    # ============================================================================
    # Numeric Patterns
    # ============================================================================

    INT = rf"\-{{0,1}}[0-9]+"
    """
    Pattern for integer numbers with optional negative sign.

    Matches:
    - Positive integers: "123", "42"
    - Negative integers: "-123", "-42"

    Note: Uses {0,1} for optional minus sign (log-surgeon syntax).
    """

    FLOAT = rf"\-{{0,1}}[0-9]+\.[0-9]+"
    """
    Pattern for floating-point numbers with optional negative sign.

    Matches:
    - Positive floats: "3.14", "123.456"
    - Negative floats: "-3.14", "-123.456"

    Requires at least one digit before and after the decimal point.
    Note: Uses {{0,1}} (escaped braces in f-string) for optional minus sign.
    """

    # ============================================================================
    # Linux File System Patterns
    # ============================================================================

    LINUX_FILE_NAME_CHARSET = rf"a-zA-Z0-9 \._\-"
    """
    Character set for Linux file names.

    Includes:
    - Alphanumeric: a-z, A-Z, 0-9
    - Common file name characters: space, . (dot), _ (underscore), - (hyphen)

    Note: This is a simplified set that covers most common file names.
    Linux technically allows many more characters in file names.
    """

    LINUX_FILE_NAME = rf"[{LINUX_FILE_NAME_CHARSET}]+"
    """
    Pattern for Linux file names.

    Matches sequences of characters commonly found in Linux file names.
    Example: "app.log", "my_file.txt", "config-2024.yaml", "data_file_v1.2.3"
    """

    LINUX_FILE_PATH = rf"([{LINUX_FILE_NAME_CHARSET}]+/)*{LINUX_FILE_NAME}+"
    """
    Pattern for Linux file paths.

    Matches relative or absolute Linux file paths with directories and file names.
    Structure: Zero or more directory segments followed by a file name.

    Examples:
    - File name only: "app.log"
    - Relative path: "logs/app.log", "var/log/app.log"
    - Multi-level: "home/user/documents/file.txt"

    Note: This pattern matches relative paths. For absolute paths starting with "/",
    you'll need to add the leading "/" separately in your pattern.
    """

    # ============================================================================
    # Character Sets and Word Patterns
    # ============================================================================

    JAVA_IDENTIFIER_CHARSET = rf"a-zA-Z0-9_"
    r"""
    Character set for Java identifier base characters.

    Includes alphanumeric characters and underscores (similar to \w in traditional regex).
    Used as building block for JAVA_IDENTIFIER and Java-related patterns.
    Note: JAVA_IDENTIFIER also includes "$" which is added separately.
    """

    JAVA_IDENTIFIER = rf"[{JAVA_IDENTIFIER_CHARSET}$]+"
    """
    Pattern for Java identifiers.

    Matches sequences of alphanumeric characters, underscores, and dollar signs.
    Java identifiers can contain letters, digits, underscores, and dollar signs.
    Example: "hello", "my_variable", "Test123", "$value", "inner$class"
    """

    LOG_LINE_CHARSET = rf" \ta-zA-Z0-9\.,:;_\-/\\\[\]\(\)\<\>=\+\*!\?@#$%\^&\|~"
    r"""
    Character set commonly found in log lines.

    Includes:
    - Whitespace: space, tab
    - Alphanumeric: a-z, A-Z, 0-9
    - Common punctuation and symbols: . , : ; _ - / \ [ ] ( ) < > = + * ! ? @ # $ % ^ & | ~

    Useful for matching general log message content.
    Note: Backslashes and special regex chars are escaped.
    """

    LOG_LINE = rf"[{LOG_LINE_CHARSET}]+"
    """
    Pattern for general log line content.

    Matches one or more characters from the LOG_LINE_CHARSET set.
    Useful for capturing general log message text that may contain various
    punctuation and symbols commonly found in logs.

    Example: "Error: connection timeout", "INFO [2024-01-01]"
    """

    LOG_LINE_NO_WHITE_SPACE_CHARSET = rf"a-zA-Z0-9\.,:;_\-/\\\[\]\(\)\<\>=\+\*!\?@#$%\^&\|~"
    r"""
    Character set commonly found in log lines, excluding whitespace.

    Includes:
    - Alphanumeric: a-z, A-Z, 0-9
    - Common punctuation and symbols: . , : ; _ - / \ [ ] ( ) < > = + * ! ? @ # $ % ^ & | ~

    Same as LOG_LINE_CHARSET but without space and tab characters.
    Useful for matching tokens or identifiers within log messages.
    Note: Backslashes and special regex chars are escaped.
    """

    LOG_LINE_NO_WHITE_SPACE = rf"[{LOG_LINE_NO_WHITE_SPACE_CHARSET}]+"
    """
    Pattern for log line content without whitespace.

    Matches one or more characters from the LOG_LINE_NO_WHITE_SPACE_CHARSET set.
    Useful for capturing individual tokens or identifiers in logs that don't
    contain spaces, such as file paths, URLs, or single-word values.

    Example: "ERROR", "connection_timeout", "/var/log/app.log", "user@example.com"
    """

    # ============================================================================
    # Java-Specific Patterns
    # ============================================================================

    JAVA_LITERAL_CHARSET = rf"a-zA-Z0-9_$"
    """
    Character set for Java identifiers.

    Java identifiers can contain letters, digits, underscores, and dollar signs.
    Note: This doesn't include all valid Java identifier start characters (e.g., Unicode).
    """

    JAVA_PACKAGE_SEGMENT = rf"[{JAVA_IDENTIFIER_CHARSET}][{JAVA_LITERAL_CHARSET}]*\."
    """
    Pattern for a single Java package segment.

    Matches one segment of a Java package name followed by a dot.
    - Must start with alphanumeric or underscore (JAVA_IDENTIFIER_CHARSET)
    - Can contain alphanumeric, underscore, or dollar sign (JAVA_LITERAL_CHARSET)
    - Ends with a dot

    Example: "com.", "example.", "my_package."
    """

    JAVA_CLASS_NAME = rf"[{JAVA_IDENTIFIER_CHARSET}][{JAVA_LITERAL_CHARSET}]+"
    """
    Pattern for a Java class name.

    Matches a valid Java class identifier:
    - Must start with alphanumeric or underscore
    - Can contain alphanumeric, underscore, or dollar sign

    Example: "MyClass", "String", "ArrayList"
    """

    JAVA_FULLY_QUALIFIED_CLASS_NAME = rf"({JAVA_PACKAGE_SEGMENT})+({JAVA_CLASS_NAME})"
    """
    Pattern for fully qualified Java class names.

    Matches complete package + class name format.
    Example: "java.util.ArrayList", "com.example.MyClass"

    Structure:
    - One or more package segments (e.g., "java.util.")
    - Followed by a class name (e.g., "ArrayList")

    Note: Uses parentheses around alternatives per log-surgeon syntax.
    """

    JAVA_LOGGING_CODE_LOCATION_HINT = rf"~\[(({LINUX_FILE_NAME})|(\?)):({INT})(\?)\]"
    """
    Pattern for Java logging code location hints.

    Matches the code location hint format used by some Java logging frameworks.
    Format: ~[filename:line?] or ~[?:line?]

    Structure:
    - Starts with ~[
    - Either a file name or "?"
    - Followed by ":"
    - Line number (INT)
    - Optional "?"
    - Ends with ]

    Example: "~[MyClass.java:42?]", "~[?:100?]"
    """

    JAVA_STACK_LOCATION = (
        rf"{JAVA_FULLY_QUALIFIED_CLASS_NAME}\({LINUX_FILE_NAME}(:{INT}){{0,1}}\))"
        rf"( {JAVA_LOGGING_CODE_LOCATION_HINT}){{0,1}}"
    )
    """
    Pattern for Java stack trace location.

    Matches Java stack trace lines showing method location and source file info.
    Combines fully qualified class name with file name and optional line number.

    Structure:
    - Fully qualified class name (e.g., "com.example.MyClass.method")
    - Opening parenthesis "("
    - File name (e.g., "MyClass.java")
    - Optional colon and line number (e.g., ":42")
    - Closing parenthesis ")"
    - Optional logging code location hint

    Examples:
    - "com.example.MyClass.method(MyClass.java:42)"
    - "java.util.ArrayList.add(ArrayList.java:123) ~[ArrayList.java:456]"
    - "org.app.Service.process(Service.java) ~[ArrayList.java:?]"
    - "org.app.Service.process(Service.java) ~[?:?]"
    - "org.app.Service.process(Service.java)"

    Note: Uses {{0,1}} for optional patterns per log-surgeon syntax.
    """
