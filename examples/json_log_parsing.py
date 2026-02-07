"""
JSON log parsing example: Extract structured data from JSON-formatted logs.

This example demonstrates how to use JsonParser to extract variables from
specific fields in JSON logs and merge the results back into the original JSON.

Features demonstrated:
- Basic JSON field extraction
- Nested field access with dot-notation
- Different conflict resolution strategies
- NDJSON and JSON array format support
- Integration with Query for DataFrame export
"""

from log_surgeon import ConflictStrategy, JsonParser, Parser, Query

# Sample JSON logs in NDJSON format (one JSON object per line)
SAMPLE_LOGS = """\
{"timestamp": "2024-01-01T10:00:00", "service": "api", "message": "Processing user=123 request id=abc123"}
{"timestamp": "2024-01-01T10:00:01", "service": "api", "message": "Error user=456 timeout status=failed"}
{"timestamp": "2024-01-01T10:00:02", "service": "worker", "message": "Completed user=789 job status=success"}
"""


def basic_example():
    """Basic example: Extract user IDs from JSON logs."""
    print("=" * 60)
    print("Basic Example: Extract user IDs from JSON logs")
    print("=" * 60)

    # Step 1: Create the underlying parser with extraction patterns
    parser = Parser()
    parser.add_var("user_info", rf"user=(?<user_id>\d+)")
    parser.add_var("request_id", rf"id=(?<request_id>[a-zA-Z0-9_]+)")
    parser.add_var("job_status", rf"status=(?<status>[a-zA-Z0-9_]+)")
    parser.compile()

    # Step 2: Create JsonParser and configure which fields to parse
    json_parser = JsonParser(parser).target_fields(["message"])

    # Step 3: Parse the logs
    print("\nInput (NDJSON):")
    for line in SAMPLE_LOGS.strip().split("\n"):
        print(f"  {line}")

    print("\nOutput (enriched JSON):")
    for enriched in json_parser.parse(SAMPLE_LOGS):
        print(
            f"  Original fields: timestamp={enriched['timestamp']}, service={enriched['service']}"
        )
        print(f"  Extracted: {enriched['extracted']}")
        print()


def nested_field_example():
    """Example: Extract from nested JSON fields using dot-notation."""
    print("=" * 60)
    print("Nested Field Example: Extract from nested JSON paths")
    print("=" * 60)

    nested_logs = """\
{"meta": {"timestamp": "2024-01-01"}, "context": {"message": "user=100 logged in"}}
{"meta": {"timestamp": "2024-01-02"}, "context": {"message": "user=200 logged out"}}
"""

    parser = Parser()
    parser.add_var("user_info", rf"user=(?<user_id>\d+)")
    parser.compile()

    # Use dot-notation to access nested fields
    json_parser = JsonParser(parser).target_fields(["context.message"])

    print("\nInput (nested JSON):")
    for line in nested_logs.strip().split("\n"):
        print(f"  {line}")

    print("\nOutput:")
    for enriched in json_parser.parse(nested_logs):
        print(f"  user_id extracted: {enriched['extracted'].get('user_id', 'N/A')}")


def conflict_strategies_example():
    """Example: Different strategies for handling key conflicts."""
    print("=" * 60)
    print("Conflict Strategies Example")
    print("=" * 60)

    # JSON where extracted key would conflict with existing key
    conflicting_log = '{"message": "user=123", "user_id": "original_value"}'

    parser = Parser()
    parser.add_var("user_info", rf"user=(?<user_id>\d+)")
    parser.compile()

    print(f"\nInput: {conflicting_log}")
    print(f"Note: 'user_id' already exists in the JSON\n")

    # Strategy 1: NEST (default, safest)
    json_parser = JsonParser(parser).target_fields(["message"])
    json_parser.on_conflict(ConflictStrategy.NEST, key="extracted")
    result = json_parser.parse_one(conflicting_log)
    print(f"NEST strategy (default):")
    print(
        f"  Result: user_id={result.get('user_id')}, extracted.user_id={result['extracted']['user_id']}"
    )

    # Strategy 2: PREFIX
    json_parser = JsonParser(parser).target_fields(["message"])
    json_parser.on_conflict(ConflictStrategy.PREFIX, prefix="parsed_")
    result = json_parser.parse_one(conflicting_log)
    print(f"\nPREFIX strategy (prefix='parsed_'):")
    print(
        f"  Result: user_id={result.get('user_id')}, parsed_user_id={result.get('parsed_user_id')}"
    )

    # Strategy 3: OVERWRITE (with warning)
    print(f"\nOVERWRITE strategy (prints warning to stderr):")
    json_parser = JsonParser(parser).target_fields(["message"])
    json_parser.on_conflict(ConflictStrategy.OVERWRITE)
    result = json_parser.parse_one(conflicting_log)
    print(f"  Result: user_id={result.get('user_id')} (original value was overwritten)")


def json_array_example():
    """Example: Parse JSON array format (alternative to NDJSON)."""
    print("=" * 60)
    print("JSON Array Example")
    print("=" * 60)

    json_array = """[
        {"message": "user=111 action=login"},
        {"message": "user=222 action=logout"},
        {"message": "user=333 action=purchase"}
    ]"""

    parser = Parser()
    parser.add_var("user_info", rf"user=(?<user_id>\d+)")
    parser.add_var("action", rf"action=(?<action>[a-zA-Z0-9_]+)")
    parser.compile()

    json_parser = JsonParser(parser).target_fields(["message"])

    print("\nInput (JSON array):")
    print(f"  {json_array}")

    print("\nOutput:")
    for enriched in json_parser.parse(json_array):
        extracted = enriched["extracted"]
        print(f"  user_id={extracted.get('user_id')}, action={extracted.get('action')}")


def query_integration_example():
    """Example: Using JsonParser with Query for DataFrame-style output."""
    print("=" * 60)
    print("Query Integration Example")
    print("=" * 60)

    parser = Parser()
    parser.add_var("user_info", rf"user=(?<user_id>\d+)")
    parser.add_var("job_status", rf"status=(?<status>[a-zA-Z0-9_]+)")
    parser.compile()

    json_parser = JsonParser(parser).target_fields(["message"])

    # Use Query to select specific fields
    query = (
        Query(json_parser)
        .select(["service", "extracted.user_id", "extracted.status"])
        .from_(SAMPLE_LOGS)
    )

    print("\nSelected fields: service, extracted.user_id, extracted.status")
    print("\nRows:")
    for row in query.get_rows():
        print(f"  {row}")

    # Filter example
    print("\nFiltered (service='api' only):")
    query = (
        Query(json_parser)
        .select(["service", "extracted.user_id"])
        .from_(SAMPLE_LOGS)
        .filter(lambda obj: obj.get("service") == "api")
    )
    for row in query.get_rows():
        print(f"  {row}")


def parse_all_strings_example():
    """Example: Extract from all string fields automatically."""
    print("=" * 60)
    print("Parse All Strings Example")
    print("=" * 60)

    log_with_multiple_fields = """\
{"primary": "user=100 logged in", "secondary": "user=200 also present", "count": 42}
"""

    parser = Parser()
    parser.add_var("user_info", rf"user=(?<user_id>\d+)")
    parser.compile()

    # target_fields("*") will extract from all string fields
    json_parser = JsonParser(parser).target_fields("*")

    print("\nInput:")
    print(f"  {log_with_multiple_fields.strip()}")

    print("\nOutput (extracted from ALL string fields):")
    for enriched in json_parser.parse(log_with_multiple_fields):
        print(f"  Extracted user_ids: {enriched['extracted'].get('user_id')}")
        print("  (Note: values from 'primary' and 'secondary' fields are aggregated)")


def include_log_type_example():
    """Example: Include log type template in output."""
    print("=" * 60)
    print("Include Log Type Example")
    print("=" * 60)

    parser = Parser()
    parser.add_var("user_info", rf"user=(?<user_id>\d+)")
    parser.add_var("action", rf"action=(?<action>[a-zA-Z0-9_]+)")
    parser.compile()

    json_parser = JsonParser(parser).target_fields(["message"]).include_log_type(True)

    sample = '{"message": "user=123 action=login completed"}'

    print(f"\nInput: {sample}")

    result = json_parser.parse_one(sample)
    print(f"\nOutput:")
    print(f"  user_id: {result['extracted']['user_id']}")
    print(f"  action: {result['extracted']['action']}")
    print(f"  @log_type: {result['extracted']['@log_type']}")
    print("  (Log type shows the template with variable placeholders)")


if __name__ == "__main__":
    basic_example()
    print()
    nested_field_example()
    print()
    conflict_strategies_example()
    print()
    json_array_example()
    print()
    query_integration_example()
    print()
    parse_all_strings_example()
    print()
    include_log_type_example()
