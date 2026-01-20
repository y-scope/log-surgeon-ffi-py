"""
Tests for JSON log parsing functionality.

This test suite validates the JsonParser class which provides JSON-aware log parsing:
- Field extraction from JSON objects using log-surgeon patterns
- Dot-notation nested field access
- Multiple conflict resolution strategies (NEST, PREFIX, OVERWRITE, RAISE)
- Support for both NDJSON and JSON array formats
- Integration with the Query class

Key concepts tested:
- Basic variable extraction from JSON fields
- Nested field access using dot-notation (e.g., "context.message")
- All conflict strategies and their behavior
- Format auto-detection (NDJSON vs JSON array)
- Warning output for OVERWRITE and PREFIX strategies
- parse_all_strings() behavior for extracting from all string fields
- Query class integration with JsonParser
"""

import io
import json

import pytest

from log_surgeon import ConflictStrategy, JsonParser, Parser, Query


@pytest.fixture
def basic_parser() -> Parser:
    """Create a basic parser with user_id extraction pattern."""
    parser = Parser()
    parser.add_var("user_info", rf"user=(?<user_id>\d+)")
    parser.compile()
    return parser


@pytest.fixture
def multi_pattern_parser() -> Parser:
    """Create a parser with multiple extraction patterns."""
    parser = Parser()
    parser.add_var("user_info", rf"user=(?<user_id>\d+)")
    parser.add_var("level", rf"(?<level>INFO|WARN|ERROR)")
    parser.add_var("status", rf"status=(?<status>\w+)")
    parser.compile()
    return parser


class TestBasicExtraction:
    """Test basic variable extraction from JSON fields."""

    def test_simple_field_extraction(self, basic_parser: Parser):
        """
        Test extracting a variable from a simple JSON field.

        Given a JSON object with a "message" field containing "user=123",
        the JsonParser should extract user_id="123" and merge it into the result.
        """
        json_parser = JsonParser(basic_parser).target_fields(["message"])

        input_json = '{"ts": "2024-01-01", "message": "Processing user=123 request"}'
        result = json_parser.parse_one(input_json)

        assert result["ts"] == "2024-01-01"
        assert result["message"] == "Processing user=123 request"
        assert result["extracted"]["user_id"] == "123"

    def test_multiple_fields_extraction(self, multi_pattern_parser: Parser):
        """
        Test extracting from multiple JSON fields.

        The parser should extract variables from all specified fields and
        aggregate them in the extracted dictionary.
        """
        json_parser = JsonParser(multi_pattern_parser).target_fields(["message", "context"])

        input_json = '{"message": "INFO user=123", "context": "status=ok"}'
        result = json_parser.parse_one(input_json)

        assert result["extracted"]["user_id"] == "123"
        assert result["extracted"]["level"] == "INFO"
        assert result["extracted"]["status"] == "ok"

    def test_no_match_returns_empty_extracted(self, basic_parser: Parser):
        """
        Test that fields with no matches still return the original JSON.

        When no patterns match, the extracted dict should be empty but the
        original JSON fields should be preserved.
        """
        json_parser = JsonParser(basic_parser).target_fields(["message"])

        input_json = '{"message": "no variables here", "other": "data"}'
        result = json_parser.parse_one(input_json)

        assert result["message"] == "no variables here"
        assert result["other"] == "data"
        assert result["extracted"] == {}


class TestDotNotationAccess:
    """Test dot-notation for accessing nested JSON fields."""

    def test_nested_field_extraction(self, basic_parser: Parser):
        """
        Test extracting from a nested JSON field using dot-notation.

        Given "context.message" as the field path, the parser should
        navigate to obj["context"]["message"] and extract variables from it.
        """
        json_parser = JsonParser(basic_parser).target_fields(["context.message"])

        input_json = '{"ts": "2024-01-01", "context": {"message": "user=456 logged in"}}'
        result = json_parser.parse_one(input_json)

        assert result["extracted"]["user_id"] == "456"

    def test_deeply_nested_field(self, basic_parser: Parser):
        """Test extracting from a deeply nested field."""
        json_parser = JsonParser(basic_parser).target_fields(["a.b.c.message"])

        input_json = '{"a": {"b": {"c": {"message": "user=789"}}}}'
        result = json_parser.parse_one(input_json)

        assert result["extracted"]["user_id"] == "789"

    def test_missing_nested_path_gracefully_skipped(self, basic_parser: Parser):
        """
        Test that missing nested paths are gracefully skipped.

        If a dot-notation path doesn't exist in the JSON, the parser should
        skip it without error.
        """
        json_parser = JsonParser(basic_parser).target_fields(["missing.path"])

        input_json = '{"message": "user=123"}'
        result = json_parser.parse_one(input_json)

        assert result["extracted"] == {}
        assert result["message"] == "user=123"


class TestConflictStrategies:
    """Test all conflict resolution strategies."""

    def test_nest_strategy_default(self, basic_parser: Parser):
        """
        Test NEST strategy (default) puts extracted vars under a key.

        NEST is the safest strategy as it avoids any key conflicts by placing
        all extracted variables under a dedicated "extracted" key.
        """
        json_parser = JsonParser(basic_parser).target_fields(["message"])
        # NEST is the default, but let's be explicit
        json_parser.on_conflict(ConflictStrategy.NEST, key="extracted")

        input_json = '{"message": "user=123"}'
        result = json_parser.parse_one(input_json)

        assert "extracted" in result
        assert result["extracted"]["user_id"] == "123"
        assert "user_id" not in result  # Not at root level

    def test_nest_strategy_custom_key(self, basic_parser: Parser):
        """Test NEST strategy with a custom key name."""
        json_parser = JsonParser(basic_parser).target_fields(["message"])
        json_parser.on_conflict(ConflictStrategy.NEST, key="parsed_data")

        input_json = '{"message": "user=123"}'
        result = json_parser.parse_one(input_json)

        assert "parsed_data" in result
        assert result["parsed_data"]["user_id"] == "123"

    def test_overwrite_strategy(self, basic_parser: Parser, capsys):
        """
        Test OVERWRITE strategy replaces existing keys with warning.

        When a conflict occurs, OVERWRITE prints a warning to stderr and
        replaces the existing value with the extracted one.
        """
        json_parser = JsonParser(basic_parser).target_fields(["message"])
        json_parser.on_conflict(ConflictStrategy.OVERWRITE)

        # user_id exists in original JSON and will be extracted
        input_json = '{"message": "user=123", "user_id": "existing_value"}'
        result = json_parser.parse_one(input_json)

        # Extracted value should overwrite
        assert result["user_id"] == "123"

        # Check warning was printed
        captured = capsys.readouterr()
        assert "Warning" in captured.err
        assert "user_id" in captured.err

    def test_prefix_strategy(self, basic_parser: Parser):
        """Test PREFIX strategy adds prefix to extracted variable names."""
        json_parser = JsonParser(basic_parser).target_fields(["message"])
        json_parser.on_conflict(ConflictStrategy.PREFIX, prefix="parsed_")

        input_json = '{"message": "user=123"}'
        result = json_parser.parse_one(input_json)

        assert "parsed_user_id" in result
        assert result["parsed_user_id"] == "123"
        assert "user_id" not in result  # Original key name not used

    def test_prefix_strategy_with_conflict_warning(self, basic_parser: Parser, capsys):
        """Test PREFIX strategy prints warning when prefixed key also conflicts."""
        json_parser = JsonParser(basic_parser).target_fields(["message"])
        json_parser.on_conflict(ConflictStrategy.PREFIX, prefix="parsed_")

        # The prefixed key already exists
        input_json = '{"message": "user=123", "parsed_user_id": "existing"}'
        result = json_parser.parse_one(input_json)

        # Should overwrite with warning
        assert result["parsed_user_id"] == "123"

        captured = capsys.readouterr()
        assert "Warning" in captured.err

    def test_raise_strategy(self, basic_parser: Parser):
        """
        Test RAISE strategy raises KeyError on conflict.

        This strategy is useful for development/testing to catch conflicts
        early rather than silently handling them.
        """
        json_parser = JsonParser(basic_parser).target_fields(["message"])
        json_parser.on_conflict(ConflictStrategy.RAISE)

        input_json = '{"message": "user=123", "user_id": "existing"}'

        with pytest.raises(KeyError) as exc_info:
            json_parser.parse_one(input_json)

        assert "user_id" in str(exc_info.value)

    def test_raise_strategy_no_conflict(self, basic_parser: Parser):
        """Test RAISE strategy works normally when no conflict exists."""
        json_parser = JsonParser(basic_parser).target_fields(["message"])
        json_parser.on_conflict(ConflictStrategy.RAISE)

        input_json = '{"message": "user=123"}'
        result = json_parser.parse_one(input_json)

        assert result["user_id"] == "123"

    def test_nest_key_conflict_preserves_original(self, basic_parser: Parser):
        """Test that when nest key already exists, original value is preserved."""
        json_parser = JsonParser(basic_parser).target_fields(["message"])
        json_parser.on_conflict(ConflictStrategy.NEST, key="extracted")

        # JSON already has "extracted" key
        input_json = '{"message": "user=123", "extracted": "original_data"}'
        result = json_parser.parse_one(input_json)

        # Original value should be preserved under "original_value"
        assert result["extracted"]["user_id"] == "123"
        assert result["extracted"]["original_value"] == "original_data"

    def test_nest_key_conflict_with_original_value_collision(self, capsys):
        """Test warning when extracted var is named 'original_value' and nest key exists."""
        parser = Parser()
        parser.add_var("val", r"val=(?<original_value>\d+)")
        parser.compile()

        json_parser = JsonParser(parser).target_fields(["message"])
        json_parser.on_conflict(ConflictStrategy.NEST, key="extracted")

        # Both: nest key exists AND extracted var named "original_value"
        input_json = '{"message": "val=999", "extracted": "preserved_value"}'
        result = json_parser.parse_one(input_json)

        # Warning should be printed
        captured = capsys.readouterr()
        assert "original_value" in captured.err

        # Original nest key value should overwrite the extracted "original_value"
        assert result["extracted"]["original_value"] == "preserved_value"


class TestNDJSONParsing:
    """Test NDJSON (newline-delimited JSON) format parsing."""

    def test_parse_ndjson_stream(self, basic_parser: Parser):
        """
        Test parsing multiple JSON lines from NDJSON format.

        NDJSON format has one JSON object per line, without wrapping array brackets.
        """
        json_parser = JsonParser(basic_parser).target_fields(["message"])

        ndjson_input = """\
{"ts": "2024-01-01", "message": "user=123 request"}
{"ts": "2024-01-02", "message": "user=456 request"}
{"ts": "2024-01-03", "message": "user=789 request"}"""

        results = list(json_parser.parse(ndjson_input))

        assert len(results) == 3
        assert results[0]["extracted"]["user_id"] == "123"
        assert results[1]["extracted"]["user_id"] == "456"
        assert results[2]["extracted"]["user_id"] == "789"

    def test_parse_ndjson_with_blank_lines(self, basic_parser: Parser):
        """Test that blank lines in NDJSON are skipped."""
        json_parser = JsonParser(basic_parser).target_fields(["message"])

        ndjson_input = """\
{"message": "user=123"}

{"message": "user=456"}

"""

        results = list(json_parser.parse(ndjson_input))

        assert len(results) == 2

    def test_parse_ndjson_from_file_object(self, basic_parser: Parser):
        """Test parsing NDJSON from a file-like object."""
        json_parser = JsonParser(basic_parser).target_fields(["message"])

        ndjson_content = '{"message": "user=123"}\n{"message": "user=456"}'
        file_obj = io.StringIO(ndjson_content)

        results = list(json_parser.parse(file_obj))

        assert len(results) == 2


class TestJSONArrayParsing:
    """Test JSON array format parsing."""

    def test_parse_json_array(self, basic_parser: Parser):
        """
        Test parsing JSON objects from an array format.

        When input starts with '[', it's treated as a JSON array.
        """
        json_parser = JsonParser(basic_parser).target_fields(["message"])

        json_array = """[
            {"ts": "2024-01-01", "message": "user=123"},
            {"ts": "2024-01-02", "message": "user=456"}
        ]"""

        results = list(json_parser.parse(json_array))

        assert len(results) == 2
        assert results[0]["extracted"]["user_id"] == "123"
        assert results[1]["extracted"]["user_id"] == "456"

    def test_auto_detect_format_ndjson(self, basic_parser: Parser):
        """Test format auto-detection correctly identifies NDJSON."""
        json_parser = JsonParser(basic_parser).target_fields(["message"])

        # Starts with '{' -> NDJSON
        ndjson_input = '{"message": "user=123"}'
        results = list(json_parser.parse(ndjson_input))

        assert len(results) == 1

    def test_auto_detect_format_json_array(self, basic_parser: Parser):
        """Test format auto-detection correctly identifies JSON array."""
        json_parser = JsonParser(basic_parser).target_fields(["message"])

        # Starts with '[' -> JSON array
        json_array = '[{"message": "user=123"}]'
        results = list(json_parser.parse(json_array))

        assert len(results) == 1


class TestParseAllStrings:
    """Test extracting from all string fields (default behavior and explicit '*')."""

    def test_default_extracts_all_strings(self, basic_parser: Parser):
        """Test that default behavior (no target_fields call) extracts from all strings."""
        json_parser = JsonParser(basic_parser)  # No target_fields() call

        input_json = '{"field1": "user=123", "field2": "user=456", "number": 42}'
        result = json_parser.parse_one(input_json)

        # Should extract from both string fields by default
        extracted_user_ids = result["extracted"]["user_id"]
        assert isinstance(extracted_user_ids, list)
        assert "123" in extracted_user_ids
        assert "456" in extracted_user_ids

    def test_parse_all_strings_flat_object(self, basic_parser: Parser):
        """Test extracting from all string fields with explicit '*'."""
        json_parser = JsonParser(basic_parser).target_fields("*")

        input_json = '{"field1": "user=123", "field2": "user=456", "number": 42}'
        result = json_parser.parse_one(input_json)

        # Should extract from both string fields
        extracted_user_ids = result["extracted"]["user_id"]
        assert isinstance(extracted_user_ids, list)
        assert "123" in extracted_user_ids
        assert "456" in extracted_user_ids

    def test_parse_all_strings_nested_object(self, basic_parser: Parser):
        """Test extracting from all string fields in nested objects."""
        json_parser = JsonParser(basic_parser).target_fields("*")

        input_json = '{"outer": {"inner": "user=123"}, "message": "user=456"}'
        result = json_parser.parse_one(input_json)

        extracted_user_ids = result["extracted"]["user_id"]
        assert isinstance(extracted_user_ids, list)
        assert "123" in extracted_user_ids
        assert "456" in extracted_user_ids

    def test_parse_all_strings_with_arrays(self, basic_parser: Parser):
        """Test extracting from string fields inside arrays."""
        json_parser = JsonParser(basic_parser).target_fields("*")

        input_json = '{"messages": ["user=123", "user=456"]}'
        result = json_parser.parse_one(input_json)

        extracted_user_ids = result["extracted"]["user_id"]
        assert isinstance(extracted_user_ids, list)
        assert "123" in extracted_user_ids
        assert "456" in extracted_user_ids


class TestIncludeLogType:
    """Test include_log_type() configuration."""

    def test_include_log_type_in_output(self, basic_parser: Parser):
        """Test that log type is included when configured."""
        json_parser = JsonParser(basic_parser).target_fields(["message"]).include_log_type(True)

        input_json = '{"message": "user=123 logged in"}'
        result = json_parser.parse_one(input_json)

        assert "@log_type" in result["extracted"]
        # The log type should contain the <user_id> placeholder
        assert "<user_id>" in result["extracted"]["@log_type"]

    def test_exclude_log_type_by_default(self, basic_parser: Parser):
        """Test that log type is excluded by default."""
        json_parser = JsonParser(basic_parser).target_fields(["message"])

        input_json = '{"message": "user=123"}'
        result = json_parser.parse_one(input_json)

        assert "@log_type" not in result["extracted"]


class TestQueryIntegration:
    """Test integration with the Query class."""

    def test_query_with_json_parser(self, basic_parser: Parser):
        """Test using Query with JsonParser for DataFrame export."""
        json_parser = JsonParser(basic_parser).target_fields(["message"])

        json_input = """\
{"message": "user=123", "service": "api"}
{"message": "user=456", "service": "web"}"""

        query = Query(json_parser).select(["service", "extracted.user_id"]).from_(json_input)
        rows = query.get_rows()

        assert len(rows) == 2
        assert rows[0] == ["api", "123"]
        assert rows[1] == ["web", "456"]

    def test_query_filter_with_json_parser(self, basic_parser: Parser):
        """Test filtering with JsonParser in Query."""
        json_parser = JsonParser(basic_parser).target_fields(["message"])

        json_input = """\
{"message": "user=123", "level": "INFO"}
{"message": "user=456", "level": "ERROR"}
{"message": "user=789", "level": "INFO"}"""

        query = (
            Query(json_parser)
            .select(["level", "extracted.user_id"])
            .from_(json_input)
            .filter(lambda obj: obj.get("level") == "ERROR")
        )
        rows = query.get_rows()

        assert len(rows) == 1
        assert rows[0] == ["ERROR", "456"]

    def test_query_validate_with_json_parser(self, basic_parser: Parser):
        """Test query validation works with JsonParser."""
        json_parser = JsonParser(basic_parser).target_fields(["message"])

        query = Query(json_parser).select(["service"]).from_('{"message": "test"}')
        validated = query.validate_query()

        assert validated is query  # Returns self


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_input(self, basic_parser: Parser):
        """Test handling of empty input."""
        json_parser = JsonParser(basic_parser).target_fields(["message"])

        results = list(json_parser.parse(""))

        assert results == []

    def test_whitespace_only_input(self, basic_parser: Parser):
        """Test handling of whitespace-only input."""
        json_parser = JsonParser(basic_parser).target_fields(["message"])

        results = list(json_parser.parse("   \n\n   "))

        assert results == []

    def test_invalid_json_raises_error(self, basic_parser: Parser):
        """Test that invalid JSON raises JSONDecodeError."""
        json_parser = JsonParser(basic_parser).target_fields(["message"])

        with pytest.raises(json.JSONDecodeError):
            json_parser.parse_one("not valid json")

    def test_non_dict_json_skipped(self, basic_parser: Parser):
        """Test that non-dict JSON values in arrays are skipped."""
        json_parser = JsonParser(basic_parser).target_fields(["message"])

        # Array contains a string, which should be skipped
        json_array = '[{"message": "user=123"}, "not a dict", {"message": "user=456"}]'
        results = list(json_parser.parse(json_array))

        # Only dict items should be processed
        assert len(results) == 2

    def test_bytes_io_input(self, basic_parser: Parser):
        """Test parsing from BytesIO input."""
        json_parser = JsonParser(basic_parser).target_fields(["message"])

        content = b'{"message": "user=123"}'
        bytes_io = io.BytesIO(content)

        results = list(json_parser.parse(bytes_io))

        assert len(results) == 1
        assert results[0]["extracted"]["user_id"] == "123"

    def test_field_not_string_is_skipped(self, basic_parser: Parser):
        """Test that non-string fields are skipped during extraction."""
        json_parser = JsonParser(basic_parser).target_fields(["count", "message"])

        input_json = '{"count": 42, "message": "user=123"}'
        result = json_parser.parse_one(input_json)

        # count is an int, should be skipped
        # message should be parsed
        assert result["extracted"]["user_id"] == "123"


class TestMethodChaining:
    """Test that all configuration methods support method chaining."""

    def test_full_chain(self, basic_parser: Parser):
        """Test chaining all configuration methods."""
        json_parser = (
            JsonParser(basic_parser)
            .target_fields(["message"])
            .on_conflict(ConflictStrategy.NEST, key="vars")
            .include_log_type(True)
        )

        input_json = '{"message": "user=123"}'
        result = json_parser.parse_one(input_json)

        assert "vars" in result
        assert result["vars"]["user_id"] == "123"
        assert "@log_type" in result["vars"]

    def test_parse_all_strings_chain(self, basic_parser: Parser):
        """Test chaining with target_fields('*')."""
        json_parser = (
            JsonParser(basic_parser)
            .target_fields("*")
            .on_conflict(ConflictStrategy.PREFIX, prefix="p_")
        )

        input_json = '{"message": "user=123"}'
        result = json_parser.parse_one(input_json)

        assert "p_user_id" in result


class TestMultipleVariableValues:
    """Test handling of multiple occurrences of the same variable."""

    def test_aggregate_multiple_values_same_field(self, basic_parser: Parser):
        """Test that multiple matches in one field are aggregated."""
        json_parser = JsonParser(basic_parser).target_fields(["message"])

        # Two user= patterns in one message
        input_json = '{"message": "user=123 then user=456"}'
        result = json_parser.parse_one(input_json)

        # Should have both values
        user_ids = result["extracted"]["user_id"]
        assert isinstance(user_ids, list)
        assert "123" in user_ids
        assert "456" in user_ids

    def test_aggregate_multiple_values_multiple_fields(self, basic_parser: Parser):
        """Test that values from multiple fields are aggregated."""
        json_parser = JsonParser(basic_parser).target_fields(["msg1", "msg2"])

        input_json = '{"msg1": "user=123", "msg2": "user=456"}'
        result = json_parser.parse_one(input_json)

        user_ids = result["extracted"]["user_id"]
        assert isinstance(user_ids, list)
        assert "123" in user_ids
        assert "456" in user_ids


class TestFlexibleTargetFieldsInput:
    """Test that target_fields accepts both string and list inputs."""

    def test_single_field_as_string(self, basic_parser: Parser):
        """Test that a single field can be passed as a string."""
        json_parser = JsonParser(basic_parser).target_fields("message")

        input_json = '{"message": "user=123", "other": "user=456"}'
        result = json_parser.parse_one(input_json)

        # Should only extract from "message", not "other"
        assert result["extracted"]["user_id"] == "123"

    def test_single_field_as_list(self, basic_parser: Parser):
        """Test that a single field can be passed as a list."""
        json_parser = JsonParser(basic_parser).target_fields(["message"])

        input_json = '{"message": "user=123", "other": "user=456"}'
        result = json_parser.parse_one(input_json)

        # Should only extract from "message", not "other"
        assert result["extracted"]["user_id"] == "123"

    def test_star_as_string(self, basic_parser: Parser):
        """Test that '*' as string targets all fields."""
        json_parser = JsonParser(basic_parser).target_fields("*")

        input_json = '{"message": "user=123", "other": "user=456"}'
        result = json_parser.parse_one(input_json)

        # Should extract from both fields
        user_ids = result["extracted"]["user_id"]
        assert isinstance(user_ids, list)
        assert "123" in user_ids
        assert "456" in user_ids

    def test_star_as_list(self, basic_parser: Parser):
        """Test that ['*'] as list targets all fields."""
        json_parser = JsonParser(basic_parser).target_fields(["*"])

        input_json = '{"message": "user=123", "other": "user=456"}'
        result = json_parser.parse_one(input_json)

        # Should extract from both fields
        user_ids = result["extracted"]["user_id"]
        assert isinstance(user_ids, list)
        assert "123" in user_ids
        assert "456" in user_ids

    def test_nested_field_as_string(self, basic_parser: Parser):
        """Test that nested field path works as a string."""
        json_parser = JsonParser(basic_parser).target_fields("context.message")

        input_json = '{"context": {"message": "user=123"}}'
        result = json_parser.parse_one(input_json)

        assert result["extracted"]["user_id"] == "123"

    def test_empty_list_raises_error(self, basic_parser: Parser):
        """Test that empty list raises ValueError with helpful message."""
        with pytest.raises(ValueError, match="fields cannot be empty"):
            JsonParser(basic_parser).target_fields([])
