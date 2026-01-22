# API Reference

For key concepts like delimiter-based matching, capture groups, and pattern syntax, see [Key Concepts](key-concepts.md).

## Parser

::: log_surgeon.Parser
    options:
      members:
        - __init__
        - add_var
        - add_timestamp
        - compile
        - parse
        - parse_event

## LogEvent

::: log_surgeon.LogEvent
    options:
      members:
        - get_log_message
        - get_log_type
        - get_capture_group
        - get_resolved_dict
        - __getitem__

## Query

::: log_surgeon.Query
    options:
      members:
        - __init__
        - select
        - filter
        - from_
        - validate_query
        - to_dataframe
        - to_arrow
        - get_rows
        - get_vars
        - get_log_types
        - get_log_type_counts

## JsonParser

::: log_surgeon.JsonParser
    options:
      members:
        - __init__
        - target_fields
        - on_conflict
        - include_log_type
        - parse
        - parse_one

## ConflictStrategy

::: log_surgeon.ConflictStrategy

## SchemaCompiler

::: log_surgeon.SchemaCompiler
    options:
      members:
        - __init__
        - add_var
        - add_timestamp
        - remove_var
        - get_var
        - compile

## PATTERN

The `PATTERN` class provides pre-built regex patterns optimized for log parsing.

::: log_surgeon.PATTERN
    options:
      members: false
      show_docstring_attributes: true
