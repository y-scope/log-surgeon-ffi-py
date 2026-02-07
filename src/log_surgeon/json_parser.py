r"""
JSON log parser that applies log-surgeon extraction rules to JSON fields.

This module provides JsonParser, a specialized parser for JSON-formatted logs.
It wraps an existing Parser instance and applies its extraction rules to
string fields within JSON objects, then merges the extracted values back
into the original JSON structure.

Key Features
------------
- Parse NDJSON (newline-delimited JSON) or JSON array formats
- Target specific fields or extract from all string fields
- Support for nested field access using dot-notation
- Configurable conflict resolution when extracted keys match existing JSON keys
- Streaming support for large NDJSON files

Example
-------
```python
from log_surgeon import JsonParser, Parser

# Create underlying parser with extraction patterns
parser = Parser()
parser.add_var("user_info", r"user=(?<user_id>\d+)")
parser.compile()

# Create JSON parser
json_parser = JsonParser(parser).target_fields(["message"])

# Parse JSON log line
result = json_parser.parse_one('{"ts": "2024-01-01", "message": "user=123"}')
print(result)
# {'ts': '2024-01-01', 'message': 'user=123', 'extracted': {'user_id': '123'}}
```

See Also
--------
Parser : The underlying parser for pattern definition.
ConflictStrategy : Enum for conflict resolution strategies.
"""

from __future__ import annotations

import io  # noqa: TC003 - used at runtime for isinstance checks
import json
import sys
from enum import auto, Enum
from typing import Any, BinaryIO, TextIO, TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Generator

from log_surgeon.parser import Parser  # noqa: TC001 - used at runtime


class ConflictStrategy(Enum):
    """
    Strategy for handling conflicts when extracted keys match existing JSON keys.

    When JsonParser extracts variables from JSON fields, the extracted key names
    might conflict with keys already present in the JSON object. This enum
    defines how such conflicts are resolved.

    Attributes
    ----------
    NEST : enum member
        Place all extracted variables under a nested key (default: "extracted").
        This is the safest option as it completely avoids conflicts.
        Result: `{"message": "...", "extracted": {"user_id": "123"}}`

    PREFIX : enum member
        Add a prefix to extracted variable names (default: "extracted.").
        Warns to stderr if the prefixed key still conflicts.
        Result: `{"message": "...", "extracted.user_id": "123"}`

    OVERWRITE : enum member
        Replace existing keys with extracted values. Prints a warning to stderr
        when overwriting occurs. Use with caution as original data is lost.
        Result: `{"user_id": "123"}` (original user_id overwritten)

    RAISE : enum member
        Raise KeyError when a conflict is detected. Useful for development
        and testing to catch unexpected conflicts early.

    Example
    -------
    ```python
    from log_surgeon import JsonParser, ConflictStrategy

    # Default: nest under "extracted" key
    json_parser = JsonParser(parser)

    # Custom nest key
    json_parser.on_conflict(ConflictStrategy.NEST, key="parsed")
    # Result: {"message": "...", "parsed": {"user_id": "123"}}

    # Use prefix instead
    json_parser.on_conflict(ConflictStrategy.PREFIX, prefix="log_")
    # Result: {"message": "...", "log_user_id": "123"}

    # Fail on conflict (for testing)
    json_parser.on_conflict(ConflictStrategy.RAISE)
    ```

    """

    OVERWRITE = auto()
    PREFIX = auto()
    NEST = auto()
    RAISE = auto()


class JsonParser:
    r"""
    Parser for JSON-formatted logs that extracts variables from string fields.

    JsonParser wraps an existing Parser and applies its extraction rules to JSON
    string fields, then merges the extracted variables back into the original JSON.
    This enables structured extraction from JSON logs while preserving the original
    JSON structure.

    Key Features
    ------------
    - **Flexible field targeting**: Extract from all strings or specific fields
    - **Nested field support**: Access nested JSON fields using dot-notation
    - **Multiple formats**: Parse NDJSON or JSON array formats with auto-detection
    - **Conflict resolution**: Configure how extracted keys merge with existing JSON
    - **Streaming support**: Efficiently process large NDJSON files line by line

    Default Behavior
    ----------------
    By default, JsonParser extracts from **all string fields** in the JSON object,
    recursively traversing nested objects and arrays. Use `target_fields()` to
    limit extraction to specific fields for better performance and precision.

    Workflow
    --------
    1. Create a Parser with extraction patterns and compile it
    2. Create a JsonParser wrapping the Parser
    3. Optionally configure target fields and conflict strategy
    4. Parse JSON logs using `parse()` or `parse_one()`

    Note
    ----
    Extraction only works on string-type fields. Non-string fields (numbers,
    booleans, nested objects, arrays) are skipped unless they contain strings.

    Example
    -------
    ```python
    from log_surgeon import JsonParser, Parser, ConflictStrategy

    # Step 1: Create and configure underlying parser
    parser = Parser()
    parser.add_var("user_info", r"user=(?<user_id>\d+)")
    parser.add_var("action", r"action=(?<action>[a-zA-Z0-9_]+)")
    parser.compile()

    # Step 2: Create JSON parser with field targeting
    json_parser = (
        JsonParser(parser)
        .target_fields(["message", "context.detail"])  # Only parse these fields
        .on_conflict(ConflictStrategy.NEST, key="extracted")
    )

    # Step 3: Parse JSON logs
    input_json = '{"ts": "2024-01-01", "message": "user=123 action=login"}'
    result = json_parser.parse_one(input_json)
    print(result)
    # {
    #     'ts': '2024-01-01',
    #     'message': 'user=123 action=login',
    #     'extracted': {'user_id': '123', 'action': 'login'}
    # }
    ```

    See Also
    --------
    Parser : For creating extraction patterns.
    ConflictStrategy : For configuring conflict resolution.
    Query : For exporting JsonParser results to DataFrames.
    """

    __slots__ = (
        "_conflict_key",
        "_conflict_prefix",
        "_conflict_strategy",
        "_field_paths_cache",
        "_fields",
        "_include_log_type",
        "_parse_all_strings_mode",
        "_parser",
    )

    def __init__(self, parser: Parser) -> None:
        r"""
        Initialize the JSON parser with an underlying Parser.

        Creates a JsonParser that applies the given Parser's extraction patterns
        to JSON string fields. By default, extracts from all string fields.

        Args:
            parser: A compiled Parser instance with extraction patterns defined.
                Must have `compile()` called before use. The parser's patterns
                will be applied to targeted JSON string fields.

        Note
        ----
        Default configuration:

        - Extracts from all string fields (equivalent to `target_fields("*")`)
        - Uses NEST conflict strategy with key "extracted"
        - Does not include log type in output

        Use the fluent API methods to customize behavior:

        - `target_fields()`: Limit which JSON fields are parsed
        - `on_conflict()`: Configure conflict resolution strategy
        - `include_log_type()`: Include log type templates in output

        Example
        -------
        ```python
        # Create and configure the underlying parser
        parser = Parser()
        parser.add_var("metric", r"value=(?<value>\d+)")
        parser.compile()

        # Create JSON parser with default settings
        json_parser = JsonParser(parser)

        # Or customize with fluent API
        json_parser = (
            JsonParser(parser)
            .target_fields(["message"])
            .on_conflict(ConflictStrategy.NEST, key="data")
            .include_log_type(True)
        )
        ```

        """
        self._parser: Parser = parser
        self._fields: list[str] | None = None
        self._field_paths_cache: dict[str, list[str]] = {}  # Cache for split field paths
        self._parse_all_strings_mode: bool = True  # Default to "*" (all string fields)
        self._conflict_strategy: ConflictStrategy = ConflictStrategy.NEST
        self._conflict_prefix: str = "extracted."
        self._conflict_key: str = "extracted"
        self._include_log_type: bool = False

    def target_fields(self, fields: list[str] | str) -> JsonParser:
        """
        Configure which JSON fields to target for variable extraction.

        By default, JsonParser extracts from all string fields in the JSON object.
        Use this method to limit extraction to specific fields for better
        performance and to avoid unintended matches in other fields.

        Args:
            fields: Field specification. Accepts:

                - `str`: Single field name (e.g., `"message"`)
                - `list[str]`: Multiple field names (e.g., `["message", "context.detail"]`)
                - `"*"` or `["*"]`: Explicitly target all string fields

                Dot-notation is supported for nested fields (e.g., `"context.message"`
                accesses `{"context": {"message": "..."}}`).

        Returns:
            Self for method chaining.

        Raises:
            ValueError: If `fields` is an empty list.

        Note
        ----
        Targeting specific fields is recommended for production use:

        - **Performance**: Avoids parsing irrelevant fields
        - **Precision**: Prevents false matches in metadata fields
        - **Clarity**: Makes extraction intent explicit

        Example
        -------
        ```python
        json_parser = JsonParser(parser)

        # Target single field
        json_parser.target_fields("message")

        # Target multiple fields (including nested)
        json_parser.target_fields(["message", "error.details", "context.info"])

        # Reset to all string fields
        json_parser.target_fields("*")
        ```

        Nested Field Example
        --------------------
        ```python
        json_data = '{"context": {"message": "user=123"}, "other": "ignored"}'

        json_parser = JsonParser(parser).target_fields(["context.message"])
        result = json_parser.parse_one(json_data)
        # Only "context.message" is parsed; "other" is ignored
        ```

        """
        # Normalize input: convert string to list, handle "*"
        if isinstance(fields, str):
            fields = [fields]

        # Validate: empty list is likely a mistake
        if fields == []:
            msg = "fields cannot be empty; omit target_fields() to extract from all strings"
            raise ValueError(msg)

        # Check for "*" (all string fields mode)
        if fields == ["*"]:
            self._fields = None
            self._parse_all_strings_mode = True
        else:
            self._fields = fields
            self._parse_all_strings_mode = False
        return self

    def on_conflict(
        self,
        strategy: ConflictStrategy,
        prefix: str = "extracted.",
        key: str = "extracted",
    ) -> JsonParser:
        """
        Configure how to handle key conflicts between extracted and existing JSON keys.

        When an extracted variable name matches an existing key in the JSON object,
        this setting determines how the conflict is resolved.

        Args:
            strategy: The conflict resolution strategy to use.
                See `ConflictStrategy` for available options.
            prefix: Prefix for extracted keys when using `ConflictStrategy.PREFIX`.
                Default: `"extracted."`. Only used with PREFIX strategy.
            key: Nesting key when using `ConflictStrategy.NEST`.
                Default: `"extracted"`. Only used with NEST strategy.

        Returns:
            Self for method chaining.

        Example
        -------
        ```python
        from log_surgeon import JsonParser, ConflictStrategy

        # NEST (default): All extracted values under a nested key
        json_parser.on_conflict(ConflictStrategy.NEST, key="parsed")
        # Input:  {"message": "user=123"}
        # Output: {"message": "user=123", "parsed": {"user_id": "123"}}

        # PREFIX: Add prefix to each extracted key
        json_parser.on_conflict(ConflictStrategy.PREFIX, prefix="log_")
        # Input:  {"message": "user=123"}
        # Output: {"message": "user=123", "log_user_id": "123"}

        # OVERWRITE: Replace existing keys (use with caution)
        json_parser.on_conflict(ConflictStrategy.OVERWRITE)
        # Input:  {"user_id": "old", "message": "user=123"}
        # Output: {"user_id": "123", "message": "user=123"}  # Warning printed

        # RAISE: Fail on conflict (for development/testing)
        json_parser.on_conflict(ConflictStrategy.RAISE)
        # Raises KeyError if extracted key exists in JSON
        ```

        """
        self._conflict_strategy = strategy
        self._conflict_prefix = prefix
        self._conflict_key = key
        return self

    def include_log_type(self, include: bool = True) -> JsonParser:
        """
        Configure whether to include log type templates in the output.

        Log types are template strings where matched variables are replaced with
        placeholders (e.g., "user=123" becomes "user=<user_id>"). They are useful
        for log clustering, pattern analysis, and anomaly detection.

        Args:
            include: If True, include "@log_type" in extracted variables.
                Default: True when this method is called.

        Returns:
            Self for method chaining.

        Note
        ----
        When enabled, each parsed field contributes its log type. If multiple
        fields are parsed, log types are aggregated.

        Example
        -------
        ```python
        json_parser = JsonParser(parser).include_log_type(True)

        result = json_parser.parse_one('{"message": "user=123 action=login"}')
        print(result["extracted"]["@log_type"])
        # "user=<user_id> action=<action>"
        ```

        """
        self._include_log_type = include
        return self

    def parse(
        self, source: str | TextIO | BinaryIO | io.StringIO | io.BytesIO
    ) -> Generator[dict[str, Any], None, None]:
        r"""
        Parse JSON logs from an input source.

        Generator that yields enriched JSON dictionaries with extracted variables
        merged in. Supports both NDJSON (newline-delimited JSON) and JSON array
        formats, with automatic format detection.

        Args:
            source: Input data to parse. Accepts:

                - `str`: String containing JSON data (NDJSON or JSON array)
                - `TextIO`: File opened in text mode
                - `BinaryIO`: File opened in binary mode
                - `io.StringIO`: In-memory text stream
                - `io.BytesIO`: In-memory binary stream

        Yields:
            dict: Enriched JSON object with extracted variables merged according
            to the configured conflict strategy.

        Raises:
            json.JSONDecodeError: If the input contains invalid JSON.
            TypeError: If the source type is not supported.

        Format Detection
        ----------------
        The format is auto-detected by checking the first non-whitespace character:

        - Starts with `[`: Parsed as JSON array (entire content loaded)
        - Otherwise: Parsed as NDJSON (streamed line by line for file objects)

        Note
        ----
        For NDJSON files, parsing is streamed line-by-line to minimize memory usage.
        JSON arrays must be fully loaded into memory for parsing.

        Example
        -------
        ```python
        # Parse NDJSON from string
        ndjson = '''{"message": "user=123"}
        {"message": "user=456"}'''

        for result in json_parser.parse(ndjson):
            print(result["extracted"]["user_id"])
        # 123
        # 456

        # Parse JSON array
        json_array = '[{"message": "user=123"}, {"message": "user=456"}]'
        for result in json_parser.parse(json_array):
            print(result["extracted"]["user_id"])

        # Stream from file
        with open("logs.ndjson") as f:
            for result in json_parser.parse(f):
                print(result)
        ```

        """
        # For strings, use non-streaming approach (already in memory)
        if isinstance(source, str):
            yield from self._parse_string(source)
            return

        # For file-like objects, try streaming for NDJSON
        yield from self._parse_file(source)

    def parse_one(self, json_line: str) -> dict[str, Any]:
        """
        Parse a single JSON object and return the enriched result.

        Convenience method for parsing a single JSON log entry. For multiple
        entries, use `parse()` instead.

        Args:
            json_line: A single JSON object as a string. Must be a valid JSON
                object (starts with `{`), not an array or primitive.

        Returns:
            Enriched JSON dictionary with the original fields plus extracted
            variables merged according to the configured conflict strategy.

        Raises:
            json.JSONDecodeError: If the input is not valid JSON.

        Example
        -------
        ```python
        result = json_parser.parse_one('{"ts": "2024-01-01", "message": "user=123"}')

        # Access original fields
        print(result["ts"])  # "2024-01-01"
        print(result["message"])  # "user=123"

        # Access extracted fields (with default NEST strategy)
        print(result["extracted"]["user_id"])  # "123"

        # Full result structure
        # {
        #     "ts": "2024-01-01",
        #     "message": "user=123",
        #     "extracted": {"user_id": "123"}
        # }
        ```

        """
        obj = json.loads(json_line)
        return self._process_json_object(obj)

    def _parse_string(self, content: str) -> Generator[dict[str, Any], None, None]:
        """Parse JSON from a string (non-streaming)."""
        content = content.strip()
        if not content:
            return

        # Auto-detect format: JSON array vs NDJSON
        if content.startswith("["):
            # JSON array format - must load all
            json_array = json.loads(content)
            for item in json_array:
                if isinstance(item, dict):
                    yield self._process_json_object(item)
        else:
            # NDJSON format
            for line in content.splitlines():
                stripped_line = line.strip()
                if stripped_line:
                    obj = json.loads(stripped_line)
                    if isinstance(obj, dict):
                        yield self._process_json_object(obj)

    def _parse_file(
        self, source: TextIO | BinaryIO | io.StringIO | io.BytesIO
    ) -> Generator[dict[str, Any], None, None]:
        """
        Parse JSON from a file-like object with streaming support for NDJSON.

        Peeks at first character to detect format. For JSON arrays, falls back
        to loading entire content. For NDJSON, streams line by line.
        """
        first_char, peeked_content = self._peek_first_char(source)
        if first_char is None:
            return  # Empty file

        if first_char == "[":
            yield from self._parse_json_array_from_file(source, peeked_content)
        else:
            yield from self._parse_ndjson_from_file(source, peeked_content)

    def _peek_first_char(
        self, source: TextIO | BinaryIO | io.StringIO | io.BytesIO
    ) -> tuple[str | None, str]:
        """Peek at first non-whitespace character, returning (char, peeked_content)."""
        peeked_content = ""
        while True:
            chunk = source.read(1)
            if not chunk:
                return None, peeked_content
            decoded = chunk.decode("utf-8") if isinstance(chunk, bytes) else chunk
            peeked_content += decoded
            if not decoded.isspace():
                return decoded, peeked_content

    def _parse_json_array_from_file(
        self, source: TextIO | BinaryIO | io.StringIO | io.BytesIO, peeked: str
    ) -> Generator[dict[str, Any], None, None]:
        """Parse JSON array format from file (must load entire content)."""
        rest = source.read()
        content = peeked + (rest.decode("utf-8") if isinstance(rest, bytes) else rest)
        for item in json.loads(content):
            if isinstance(item, dict):
                yield self._process_json_object(item)

    def _parse_ndjson_from_file(
        self, source: TextIO | BinaryIO | io.StringIO | io.BytesIO, peeked: str
    ) -> Generator[dict[str, Any], None, None]:
        """Parse NDJSON format from file with streaming."""
        # Handle first line (includes peeked content)
        first_line_rest = source.readline()
        first_line = peeked + (
            first_line_rest.decode("utf-8")
            if isinstance(first_line_rest, bytes)
            else first_line_rest
        )
        yield from self._process_json_line(first_line)

        # Stream remaining lines
        for raw_line in source:
            line = raw_line.decode("utf-8") if isinstance(raw_line, bytes) else raw_line
            yield from self._process_json_line(line)

    def _process_json_line(self, line: str) -> Generator[dict[str, Any], None, None]:
        """Process a single JSON line, yielding result if valid dict."""
        stripped = line.strip()
        if stripped:
            obj = json.loads(stripped)
            if isinstance(obj, dict):
                yield self._process_json_object(obj)

    def _process_json_object(self, obj: dict[str, Any]) -> dict[str, Any]:
        """
        Process a single JSON object, extracting variables and merging.

        Args:
            obj: JSON object to process.

        Returns:
            Enriched JSON object with extracted variables.

        """
        extracted: dict[str, Any] = {}

        if self._parse_all_strings_mode:
            # Parse all string fields
            self._extract_from_all_strings(obj, extracted)
        elif self._fields:
            # Parse specific fields
            for field_path in self._fields:
                field_value = self._get_field_value(obj, field_path)
                if field_value is not None and isinstance(field_value, str):
                    self._extract_from_field(field_value, extracted)

        # Merge extracted variables back into the original object
        return self._merge_extracted(obj, extracted)

    def _extract_from_all_strings(self, obj: Any, extracted: dict[str, Any]) -> None:
        """
        Recursively extract variables from all string fields in an object.

        Args:
            obj: Object to extract from (dict, list, or value).
            extracted: Dictionary to store extracted variables.

        """
        if isinstance(obj, dict):
            for value in obj.values():
                self._extract_from_all_strings(value, extracted)
        elif isinstance(obj, list):
            for item in obj:
                self._extract_from_all_strings(item, extracted)
        elif isinstance(obj, str):
            self._extract_from_field(obj, extracted)

    def _extract_from_field(self, field_value: str, extracted: dict[str, Any]) -> None:
        """
        Extract variables from a field value using the underlying parser.

        Args:
            field_value: String value to parse.
            extracted: Dictionary to store extracted variables.

        """
        event = self._parser.parse_event(field_value)
        if event is None:
            return

        resolved = event.get_resolved_dict()
        for key, value in resolved.items():
            # Skip timestamp fields (handled separately in get_resolved_dict)
            if key == "timestamp":
                continue
            self._aggregate_value(extracted, key, value)

        # Include log type if configured
        if self._include_log_type:
            self._aggregate_value(extracted, "@log_type", event.get_log_type())

    def _aggregate_value(self, extracted: dict[str, Any], key: str, value: Any) -> None:
        """
        Aggregate a value into the extracted dictionary, handling duplicates.

        Args:
            extracted: Dictionary to store extracted variables.
            key: Key to store the value under.
            value: Value to store or aggregate.

        """
        if key not in extracted:
            extracted[key] = value
            return

        existing = extracted[key]
        if isinstance(existing, list):
            if isinstance(value, list):
                existing.extend(value)
            else:
                existing.append(value)
        elif isinstance(value, list):
            extracted[key] = [existing, *value]
        else:
            extracted[key] = [existing, value]

    def _get_field_value(self, obj: dict[str, Any], path: str) -> Any | None:
        """
        Get a field value using dot-notation path.

        Uses cached path splits to avoid repeated string splitting.

        Args:
            obj: Dictionary to extract from.
            path: Dot-separated path to the field (e.g., "context.message").

        Returns:
            Field value or None if not found.

        Example:
            ```python
            obj = {"context": {"message": "hello"}}
            _get_field_value(obj, "context.message")  # 'hello'
            ```

        """
        # Use cached split or compute and cache
        if path not in self._field_paths_cache:
            self._field_paths_cache[path] = path.split(".")
        parts = self._field_paths_cache[path]

        current: Any = obj
        for part in parts:
            if not isinstance(current, dict) or part not in current:
                return None
            current = current[part]
        return current

    def _merge_extracted(
        self, obj: dict[str, Any], extracted: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Merge extracted variables into the JSON object.

        Modifies obj in place. This is safe because obj always comes from
        json.loads() which creates fresh dicts.

        Args:
            obj: JSON object to modify (from json.loads).
            extracted: Extracted variables to merge.

        Returns:
            The modified JSON object.

        """
        if self._conflict_strategy == ConflictStrategy.NEST:
            # Handle conflict when nest key already exists
            if self._conflict_key in obj:
                original_value = obj[self._conflict_key]
                if "original_value" in extracted:
                    self._warn_conflict("original_value")
                extracted["original_value"] = original_value
            obj[self._conflict_key] = extracted
        elif not extracted:
            # For other strategies, return early if nothing to merge
            return obj
        elif self._conflict_strategy == ConflictStrategy.PREFIX:
            self._merge_with_prefix(obj, extracted)
        elif self._conflict_strategy == ConflictStrategy.OVERWRITE:
            self._merge_with_overwrite(obj, extracted)
        elif self._conflict_strategy == ConflictStrategy.RAISE:
            self._merge_with_raise(obj, extracted)

        return obj

    def _merge_with_prefix(self, result: dict[str, Any], extracted: dict[str, Any]) -> None:
        """Merge extracted vars with prefix, warning on conflict."""
        for key, value in extracted.items():
            prefixed_key = f"{self._conflict_prefix}{key}"
            if prefixed_key in result:
                self._warn_conflict(prefixed_key)
            result[prefixed_key] = value

    def _merge_with_overwrite(self, result: dict[str, Any], extracted: dict[str, Any]) -> None:
        """Merge extracted vars directly, warning on conflict."""
        for key, value in extracted.items():
            if key in result:
                self._warn_conflict(key)
            result[key] = value

    def _merge_with_raise(self, result: dict[str, Any], extracted: dict[str, Any]) -> None:
        """Merge extracted vars, raising error on conflict."""
        for key, value in extracted.items():
            if key in result:
                msg = f"Conflict: Key '{key}' already exists in JSON object"
                raise KeyError(msg)
            result[key] = value

    def _warn_conflict(self, key: str) -> None:
        """Print a warning about a key conflict to stderr."""
        print(  # noqa: T201
            f"Warning: Key '{key}' already exists, overwriting",
            file=sys.stderr,
        )
