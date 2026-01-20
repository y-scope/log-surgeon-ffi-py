"""JSON log parser that applies log-surgeon extraction rules to JSON fields."""

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
    Strategy for handling conflicts when extracted variable names match existing JSON keys.

    Attributes:
        OVERWRITE: Replace existing key with extracted value (prints warning to stderr)
        PREFIX: Add configurable prefix to extracted variable names (prints warning on conflict)
        NEST: Put all extracted variables under a nested key (default, safest - avoids conflicts)
        RAISE: Raise KeyError on conflict (for development/testing)

    Example:
        >>> json_parser.on_conflict(ConflictStrategy.NEST, key="extracted")
        >>> # Result: {"message": "...", "extracted": {"user_id": "123"}}

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

    By default, extraction is applied to all string fields in the JSON object.
    Use target_fields() to limit extraction to specific fields.

    Note:
        Extraction only works on string-type fields. Non-string fields (numbers,
        booleans, objects, arrays) are skipped during extraction.

    Example:
        >>> from log_surgeon import JsonParser, Parser
        >>>
        >>> # Create underlying parser with extraction patterns
        >>> parser = Parser()
        >>> parser.add_var("user_info", r"user=(?<user_id>\d+)")
        >>> parser.compile()
        >>>
        >>> # Create JSON parser (defaults to extracting from all string fields)
        >>> json_parser = JsonParser(parser)
        >>>
        >>> # Parse JSON logs
        >>> input_json = '{"ts": "2024-01-01", "message": "user=123 request"}'
        >>> result = json_parser.parse_one(input_json)
        >>> print(result)
        {'ts': '2024-01-01', 'message': 'user=123 request', 'extracted': {'user_id': '123'}}

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
        """
        Initialize the JSON parser with an underlying Parser.

        By default, the parser extracts from all string fields ("*" mode).
        Use target_fields() to specify specific fields instead.

        Args:
            parser: A configured and compiled Parser instance for log parsing.
                The parser should have variables added via add_var() and be compiled.

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

        By default (if this method is not called), JsonParser extracts from all
        string fields. Use this method to limit extraction to specific fields,
        or pass "*" to explicitly extract from all string fields.

        Args:
            fields: Field specification. Can be:
                - A single field name as a string (e.g., "message")
                - A list of field names (e.g., ["message", "context.detail"])
                - "*" or ["*"] to explicitly target all string fields
                Supports dot-notation for nested fields.

        Returns:
            Self for method chaining.

        Example:
            >>> # Default: extracts from all string fields
            >>> json_parser = JsonParser(parser)
            >>>
            >>> # Limit to specific field (string or list)
            >>> json_parser.target_fields("message")
            >>> json_parser.target_fields(["message"])
            >>>
            >>> # Multiple fields
            >>> json_parser.target_fields(["message", "context.detail"])
            >>>
            >>> # Explicitly target all string fields
            >>> json_parser.target_fields("*")
            >>> json_parser.target_fields(["*"])

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
        Configure how to handle conflicts when extracted keys exist in original JSON.

        Args:
            strategy: The conflict resolution strategy to use.
            prefix: Prefix to add to extracted variable names when using PREFIX strategy.
            key: Key under which to nest extracted variables when using NEST strategy.

        Returns:
            Self for method chaining.

        Example:
            >>> # Nest all extracted variables under "extracted" key
            >>> json_parser.on_conflict(ConflictStrategy.NEST, key="extracted")
            >>>
            >>> # Add prefix to extracted variable names
            >>> json_parser.on_conflict(ConflictStrategy.PREFIX, prefix="parsed_")

        """
        self._conflict_strategy = strategy
        self._conflict_prefix = prefix
        self._conflict_key = key
        return self

    def include_log_type(self, include: bool = True) -> JsonParser:
        """
        Configure whether to include the log type in the output.

        Args:
            include: If True, include "@log_type" in extracted variables.

        Returns:
            Self for method chaining.

        """
        self._include_log_type = include
        return self

    def parse(
        self, source: str | TextIO | BinaryIO | io.StringIO | io.BytesIO
    ) -> Generator[dict[str, Any], None, None]:
        """
        Parse JSON logs from an input source.

        Supports both NDJSON (newline-delimited JSON) and JSON array formats.
        Auto-detects the format based on whether the input starts with '['.

        For NDJSON with file objects, uses streaming to avoid loading entire
        file into memory.

        Args:
            source: Input data to parse. Can be:
                - str: Plain string containing JSON data
                - TextIO: Text file object
                - BinaryIO: Binary file object
                - io.StringIO: String buffer
                - io.BytesIO: Bytes buffer

        Yields:
            Enriched JSON dictionaries with extracted variables merged in.

        Raises:
            json.JSONDecodeError: If the input is not valid JSON.
            TypeError: If the source type is not supported.

        Example:
            >>> for enriched in json_parser.parse(ndjson_input):
            ...     print(enriched)

        """
        # For strings, use non-streaming approach (already in memory)
        if isinstance(source, str):
            yield from self._parse_string(source)
            return

        # For file-like objects, try streaming for NDJSON
        yield from self._parse_file(source)

    def parse_one(self, json_line: str) -> dict[str, Any]:
        """
        Parse a single JSON line and return the enriched dictionary.

        Args:
            json_line: A single JSON object as a string.

        Returns:
            Enriched JSON dictionary with extracted variables merged in.

        Raises:
            json.JSONDecodeError: If the input is not valid JSON.

        Example:
            >>> result = json_parser.parse_one('{"message": "user=123"}')
            >>> print(result["extracted"]["user_id"])
            123

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
            >>> obj = {"context": {"message": "hello"}}
            >>> _get_field_value(obj, "context.message")
            'hello'

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
