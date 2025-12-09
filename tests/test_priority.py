"""Tests for variable priority and ordering functionality.

This test suite validates the priority-based ordering system for schema variables.
Variables can be assigned priority values (similar to CSS z-index) to control their
order in the compiled schema. Higher priority variables appear first, which affects
matching precedence in the parser.

Sorting Algorithm:
    Variables are sorted using a two-level key:
    1. Priority (descending): Higher priority values appear first
    2. Insertion order (ascending): For same priority, earlier insertions appear first

    Formula: sorted(vars, key=lambda v: (-v.priority, v.insertion_order))

Key concepts tested:
- Priority ordering (higher values appear first)
- Insertion order preservation (stable sort for same priority)
- Negative priorities for generic/fallback patterns
- Integration with Parser API and actual parsing behavior
- Timestamp precedence (always first regardless of priority)

Common Use Cases:
    - High priority (e.g., 100): Specific patterns like "USER:12345" or custom formats
    - Default priority (0): Normal patterns added by users
    - Negative priority (e.g., -1, -10): Generic fallback patterns like integers or floats
"""

import pytest

from log_surgeon import Parser, PATTERN, SchemaCompiler


class TestVariablePriority:
    """Test suite for variable priority ordering in schema compilation."""

    def test_default_priority_maintains_insertion_order(self):
        """
        Test that variables with default priority (0) maintain their insertion order.

        When no explicit priority is specified, all variables default to priority 0.
        Variables with the same priority should appear in the schema in the same order
        they were added (insertion order).

        Expected behavior:
        - All variables have priority 0 (default)
        - Schema order matches insertion order: first, second, third
        - Hidden variable IDs: 0, 1, 2 (sequential)
        """
        compiler = SchemaCompiler()
        compiler.add_var("first", rf"(?<a>\d+)")       # priority 0 (default), ID 0
        compiler.add_var("second", rf"(?<b>\w+)")      # priority 0 (default), ID 1
        compiler.add_var("third", rf"(?<c>[A-Z]+)")    # priority 0 (default), ID 2

        schema = compiler.compile()
        lines = schema.split("\n")
        var_lines = [l for l in lines if ":" in l and not l.startswith("//") and not l.startswith("delimiters")]

        # Verify variables appear in insertion order (0, 1, 2)
        assert "LogSurgeonHiddenVariables0" in var_lines[0]  # first
        assert "LogSurgeonHiddenVariables1" in var_lines[1]  # second
        assert "LogSurgeonHiddenVariables2" in var_lines[2]  # third

    def test_higher_priority_appears_first(self):
        """
        Test that variables are ordered by priority (highest first).

        Variables with different priorities should appear in descending priority order
        in the compiled schema, regardless of their insertion order.

        Test setup:
        - "low" variable: priority -1, inserted first, ID 0
        - "medium" variable: priority 0, inserted second, ID 1
        - "high" variable: priority 10, inserted third, ID 2

        Expected schema order (by priority):
        1. high (priority 10, ID 2)
        2. medium (priority 0, ID 1)
        3. low (priority -1, ID 0)

        This demonstrates that priority overrides insertion order.
        """
        compiler = SchemaCompiler()
        compiler.add_var("low", rf"(?<low>\d+)", priority=-1)      # ID 0
        compiler.add_var("medium", rf"(?<med>\w+)", priority=0)    # ID 1
        compiler.add_var("high", rf"(?<high>[A-Z]+)", priority=10) # ID 2

        # Verify vars are stored in insertion order (not priority order)
        assert compiler.vars[0].priority == -1  # low (inserted first)
        assert compiler.vars[1].priority == 0   # medium (inserted second)
        assert compiler.vars[2].priority == 10  # high (inserted third)

        # Verify compiled schema orders by priority (not insertion order)
        schema = compiler.compile()
        lines = schema.split("\n")
        var_lines = [l for l in lines if "LogSurgeonHiddenVariables" in l]

        # Extract hidden variable IDs from compiled schema
        hidden_ids = [line.split(":")[0].strip() for line in var_lines]

        # Assert correct priority-based ordering
        assert len(hidden_ids) == 3
        assert hidden_ids[0] == "LogSurgeonHiddenVariables2"  # high (priority 10)
        assert hidden_ids[1] == "LogSurgeonHiddenVariables1"  # medium (priority 0)
        assert hidden_ids[2] == "LogSurgeonHiddenVariables0"  # low (priority -1)

    def test_negative_priority_lower_than_zero(self):
        """
        Test that negative priority variables appear after priority 0 variables.

        Negative priorities are useful for generic fallback patterns that should only
        match when no higher-priority patterns match. Priority 0 is the default and
        represents "normal" priority.

        Test setup:
        - "generic" variable: pattern matches any digits, priority -1 (fallback), ID 0
        - "specific" variable: pattern matches exactly 3 digits, priority 0 (default), ID 1

        Expected schema order:
        1. specific (priority 0, ID 1) - more specific pattern, higher priority
        2. generic (priority -1, ID 0) - generic fallback pattern

        Use case: When parsing "123", we want the specific 3-digit pattern to match
        before falling back to the generic digit pattern.
        """
        compiler = SchemaCompiler()
        compiler.add_var("generic", rf"(?<num>\d+)", priority=-1)     # ID 0, fallback
        compiler.add_var("specific", rf"(?<val>\d{{3}})", priority=0) # ID 1, default

        schema = compiler.compile()
        lines = schema.split("\n")
        var_lines = [l for l in lines if "LogSurgeonHiddenVariables" in l]

        # Extract hidden variable IDs from compiled schema
        hidden_ids = [line.split(":")[0].strip() for line in var_lines]

        # Verify specific pattern (priority 0) appears before generic (priority -1)
        assert len(hidden_ids) == 2
        assert hidden_ids[0] == "LogSurgeonHiddenVariables1"  # specific (priority 0)
        assert hidden_ids[1] == "LogSurgeonHiddenVariables0"  # generic (priority -1)

    def test_same_priority_maintains_insertion_order(self):
        """
        Test that variables with the same priority maintain insertion order.

        When multiple variables have the same priority, they should be ordered by the
        sequence in which they were added (stable sort). This ensures predictable and
        deterministic behavior.

        Test setup:
        - "alpha" variable: priority 5, inserted first, ID 0
        - "beta" variable: priority 5, inserted second, ID 1
        - "gamma" variable: priority 5, inserted third, ID 2

        Expected schema order (by insertion order, since all have priority 5):
        1. alpha (ID 0)
        2. beta (ID 1)
        3. gamma (ID 2)

        This test validates the stable sort behavior: when priorities are equal,
        the secondary sort key is insertion order.
        """
        compiler = SchemaCompiler()
        compiler.add_var("alpha", rf"(?<a>a+)", priority=5)  # ID 0
        compiler.add_var("beta", rf"(?<b>b+)", priority=5)   # ID 1
        compiler.add_var("gamma", rf"(?<c>c+)", priority=5)  # ID 2

        schema = compiler.compile()
        lines = schema.split("\n")
        var_lines = [l for l in lines if "LogSurgeonHiddenVariables" in l]

        # Extract hidden variable IDs from compiled schema
        hidden_ids = [line.split(":")[0].strip() for line in var_lines]

        # Verify insertion order is preserved when priorities are equal
        assert len(hidden_ids) == 3
        assert hidden_ids[0] == "LogSurgeonHiddenVariables0"  # alpha (inserted first)
        assert hidden_ids[1] == "LogSurgeonHiddenVariables1"  # beta (inserted second)
        assert hidden_ids[2] == "LogSurgeonHiddenVariables2"  # gamma (inserted third)

    def test_mixed_priorities_correct_ordering(self):
        """
        Test complex real-world scenario with multiple priority levels and same-priority groups.

        This test validates the complete sorting algorithm with:
        - Multiple priority levels (high, normal, and fallback)
        - Multiple variables at the same priority (normal1 and normal2)
        - Negative priorities for generic fallback patterns

        Test setup (insertion order):
        1. fallback_int: priority -10, generic integer pattern, ID 0
        2. fallback_float: priority -5, generic float pattern, ID 1
        3. normal1: priority 0 (default), word pattern, ID 2
        4. normal2: priority 0 (default), lowercase pattern, ID 3
        5. high_prio: priority 100, specific ID pattern, ID 4

        Expected schema order (sorted by priority desc, then insertion order asc):
        1. high_prio (priority 100, ID 4) - most specific, highest priority
        2. normal1 (priority 0, ID 2) - default priority, inserted first
        3. normal2 (priority 0, ID 3) - default priority, inserted second
        4. fallback_float (priority -5, ID 1) - generic fallback, higher than -10
        5. fallback_int (priority -10, ID 0) - most generic fallback

        This represents a typical log parsing scenario where:
        - Specific patterns (like IDs) have high priority
        - Normal patterns use default priority
        - Generic numeric fallbacks have negative priority
        """
        compiler = SchemaCompiler()
        compiler.add_var("fallback_int", rf"(?<int>\d+)", priority=-10)                     # ID 0
        compiler.add_var("fallback_float", rf"(?<float>{PATTERN.FLOAT})", priority=-5)      # ID 1
        compiler.add_var("normal1", rf"(?<n1>\w+)", priority=0)                             # ID 2
        compiler.add_var("normal2", rf"(?<n2>[a-z]+)", priority=0)                          # ID 3
        compiler.add_var("high_prio", rf"(?<hp>ID\d{{6}})", priority=100)                   # ID 4

        schema = compiler.compile()
        lines = schema.split("\n")
        var_lines = [l for l in lines if "LogSurgeonHiddenVariables" in l]

        # Extract hidden variable IDs from compiled schema
        hidden_ids = [line.split(":")[0].strip() for line in var_lines]

        # Verify all 5 variables are present
        assert len(hidden_ids) == 5

        # Verify correct ordering: priority descending, insertion order ascending
        assert hidden_ids[0] == "LogSurgeonHiddenVariables4"  # high_prio (priority 100)
        assert hidden_ids[1] == "LogSurgeonHiddenVariables2"  # normal1 (priority 0, first)
        assert hidden_ids[2] == "LogSurgeonHiddenVariables3"  # normal2 (priority 0, second)
        assert hidden_ids[3] == "LogSurgeonHiddenVariables1"  # fallback_float (priority -5)
        assert hidden_ids[4] == "LogSurgeonHiddenVariables0"  # fallback_int (priority -10)

    def test_parser_priority_integration(self):
        r"""
        Test that priority affects actual parsing behavior through the Parser API.

        This integration test validates that the priority system works end-to-end:
        from schema compilation through parsing to result extraction. The priority
        should affect which pattern matches when multiple patterns could match the
        same input.

        Test setup:
        - generic_num: matches any sequence of digits, priority -1 (fallback)
        - specific_id: matches "USER:" followed by exactly 4 digits, priority 1 (higher)

        Test input: "USER:1234"
        - Both patterns could theoretically match the digits "1234"
        - But specific_id (priority 1) should match before generic_num (priority -1)

        Expected result:
        - The specific_id pattern matches
        - Capture group "id" contains "1234"
        - Capture group "num" is not set (generic_num didn't match)

        This demonstrates that priority affects parse precedence, ensuring more
        specific patterns match before generic fallback patterns.
        """
        parser = Parser()
        parser.add_var("generic_num", rf"(?<num>\d+)", priority=-1)           # Fallback
        parser.add_var("specific_id", rf"USER:(?<id>\d{{4}})", priority=1)    # Higher priority

        # Compile the schema with priority-based ordering
        parser.compile()

        # Parse input that could match both patterns
        event = parser.parse_event("USER:1234")

        # Verify the higher-priority specific pattern matched
        assert event is not None
        assert event.get_capture_group("id") == "1234"  # specific_id matched
        # Note: generic_num should not match because specific_id has higher priority

    def test_timestamps_unaffected_by_priority(self):
        r"""
        Test that timestamps always appear first, regardless of variable priorities.

        Timestamps are special anchoring patterns that define log event boundaries.
        They must always appear first in the schema, before any variables, regardless
        of any priority values assigned to variables. This is a structural requirement
        of the log-surgeon schema format.

        Test setup:
        - One timestamp pattern (date in YYYY/MM/DD format)
        - high_priority variable with priority 100
        - low_priority variable with priority -100

        Expected schema structure:
        1. Delimiter section
        2. Timestamp section (always first, before variables)
        3. Variable section (ordered by priority)

        This test verifies that even extremely high priority values (100 or higher)
        cannot move a variable before the timestamp section.
        """
        compiler = SchemaCompiler()
        compiler.add_timestamp("ts", r"\d{4}/\d{2}/\d{2}")  # Date: YYYY/MM/DD
        compiler.add_var("high_priority", rf"(?<hp>test)", priority=100)   # Very high
        compiler.add_var("low_priority", rf"(?<lp>data)", priority=-100)   # Very low

        schema = compiler.compile()
        lines = schema.split("\n")

        # Locate the timestamp and variable section markers
        timestamp_section_idx = None
        var_section_idx = None
        for i, line in enumerate(lines):
            if "// schema timestamps" in line:
                timestamp_section_idx = i
            if "// schema variables" in line:
                var_section_idx = i

        # Verify timestamps appear before variables in the schema
        assert timestamp_section_idx is not None, "Timestamp section should exist"
        assert var_section_idx is not None, "Variable section should exist"
        assert timestamp_section_idx < var_section_idx, "Timestamps must appear before variables"

    def test_insertion_order_counter_increments(self):
        """
        Test that the insertion_order counter increments sequentially.

        The insertion_order attribute is used as a secondary sort key when variables
        have the same priority. This test validates that each variable gets a unique,
        sequential insertion order value starting from 0.

        Test setup:
        - Add three variables with the same priority (0)
        - All are stored in the internal vars list

        Expected behavior:
        - var1 has insertion_order = 0 (added first)
        - var2 has insertion_order = 1 (added second)
        - var3 has insertion_order = 2 (added third)

        This internal counter ensures deterministic ordering when priorities are equal.
        """
        compiler = SchemaCompiler()

        # Add three variables with identical priority
        compiler.add_var("var1", rf"(?<v1>\d+)", priority=0)
        compiler.add_var("var2", rf"(?<v2>\w+)", priority=0)
        compiler.add_var("var3", rf"(?<v3>[A-Z]+)", priority=0)

        # Verify sequential insertion order values
        assert compiler.vars[0].insertion_order == 0, "First variable should have insertion_order 0"
        assert compiler.vars[1].insertion_order == 1, "Second variable should have insertion_order 1"
        assert compiler.vars[2].insertion_order == 2, "Third variable should have insertion_order 2"

    def test_priority_attribute_stored_correctly(self):
        """
        Test that priority values are stored correctly in Variable objects.

        This test validates that the priority parameter passed to add_var() is
        correctly stored in the Variable object's priority attribute. This is a
        basic unit test for the data storage mechanism.

        Test setup:
        - high: priority 10
        - medium: priority 0 (default)
        - low: priority -5

        Expected behavior:
        - Each Variable object stores its assigned priority value
        - Priority values can be positive, zero, or negative
        - Values are stored as integers

        This test accesses the internal vars list directly to verify the priority
        attribute is set correctly before any sorting occurs.
        """
        compiler = SchemaCompiler()

        compiler.add_var("high", rf"(?<h>\d+)", priority=10)    # Positive priority
        compiler.add_var("medium", rf"(?<m>\d+)", priority=0)   # Zero (default)
        compiler.add_var("low", rf"(?<l>\d+)", priority=-5)     # Negative priority

        # Verify priority values are stored correctly (in insertion order)
        assert compiler.vars[0].priority == 10, "First variable should have priority 10"
        assert compiler.vars[1].priority == 0, "Second variable should have priority 0"
        assert compiler.vars[2].priority == -5, "Third variable should have priority -5"
