"""Adapter bridging the Rust lexer to LogEvent objects."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Generator
    from typing import Self

    from log_surgeon.schema_compiler import SchemaCompiler

from log_surgeon._rust_ffi import ffi, lib, make_string_view, read_string_view
from log_surgeon.log_event import LogEvent

# Shorthand character class expansions for the Rust regex parser, which does
# not yet natively support \d, \w, \s.  These mappings are applied in Python
# so the Rust parser only sees explicit character classes.
_SHORTHAND_OUTSIDE: dict[str, str] = {
    "d": "[0-9]",
    "D": "[^0-9]",
    "w": "[a-zA-Z0-9_]",
    "W": "[^a-zA-Z0-9_]",
    "s": r"[ \t\r\n]",
    "S": r"[^ \t\r\n]",
}
_SHORTHAND_INSIDE: dict[str, str] = {
    "d": "0-9",
    "D": "^0-9",
    "w": "a-zA-Z0-9_",
    "W": "^a-zA-Z0-9_",
    "s": r" \t\r\n",
    "S": r"^ \t\r\n",
}


def _translate_shorthand_classes(pattern: str) -> str:
    r"""
    Translate \d, \w, \s shorthand classes to explicit character classes.

    The Rust regex parser does not support shorthand character classes yet.
    This rewrites them before the pattern reaches the Rust layer:

    Outside ``[...]``: ``\d`` → ``[0-9]``, ``\s`` → ``[ \t\r\n]``, etc.
    Inside  ``[...]``: ``\d`` → ``0-9`` (bare ranges, no extra brackets).
    """
    result: list[str] = []
    i = 0
    in_bracket = False

    while i < len(pattern):
        ch = pattern[i]

        # Handle escape sequences
        if ch == "\\" and i + 1 < len(pattern):
            next_ch = pattern[i + 1]
            table = _SHORTHAND_INSIDE if in_bracket else _SHORTHAND_OUTSIDE
            if next_ch in table:
                result.append(table[next_ch])
                i += 2
                continue
            # Not a shorthand — keep the escape as-is
            result.append(ch)
            result.append(next_ch)
            i += 2
            continue

        # Track character class nesting (only one level in standard regex)
        if ch == "[" and not in_bracket:
            in_bracket = True
        elif ch == "]" and in_bracket:
            in_bracket = False

        result.append(ch)
        i += 1

    return "".join(result)


# Type alias for a collected fragment's data:
# (match_start_byte, match_end_byte, is_event_start,
#  [(cap_name, cap_value, cap_start_byte, cap_end_byte)])
FragmentData = tuple[int, int, bool, list[tuple[str, str, int, int]]]


class RustBackend:
    """Uses the Rust log-mechanic lexer and reconstructs LogEvent objects in Python."""

    def __init__(self, schema_compiler: SchemaCompiler, debug: bool) -> None:
        # Initialize pointers early so close() is safe even if __init__ fails partway.
        self._schema = ffi.NULL
        self._lexer = ffi.NULL
        self._kept_alive: list[bytes] = []
        self._rule_names: set[str] = set()
        self._timestamp_rule_names: set[str] = set()

        lib.clp_log_mechanic_set_debug(debug)
        self._schema = lib.clp_log_mechanic_schema_new()

        # Set delimiters
        delimiters_bytes = schema_compiler.decoded_delimiters.encode("utf-8")
        self._kept_alive.append(delimiters_bytes)
        if not lib.clp_log_mechanic_schema_set_delimiters(
            self._schema, make_string_view(delimiters_bytes)
        ):
            msg = "Failed to set delimiters on Rust schema"
            raise RuntimeError(msg)

        # Add rules in same priority order as C++ backend
        sorted_vars = sorted(schema_compiler.vars, key=lambda v: (-v.priority, v.insertion_order))

        # _rule_names tracks all rule names so we can filter out the implicit
        # whole-match capture the Rust engine emits for each rule.
        # _timestamp_rule_names: whole-match capture is stored as "firstTimestamp"
        # and appears as "<timestamp>" in log types, matching C++ backend behavior.

        # Add timestamp rules first (they get highest precedence like C++)
        for ts_name, ts_regex in schema_compiler.timestamps.items():
            name_bytes = ts_name.encode("utf-8")
            regex_bytes = _translate_shorthand_classes(ts_regex).encode("utf-8")
            self._kept_alive.extend([name_bytes, regex_bytes])
            if not lib.clp_log_mechanic_schema_add_timestamp_rule(
                self._schema, make_string_view(name_bytes), make_string_view(regex_bytes)
            ):
                msg = f"Failed to add timestamp rule '{ts_name}' with pattern '{ts_regex}'"
                raise RuntimeError(msg)
            self._rule_names.add(ts_name)
            self._timestamp_rule_names.add(ts_name)

        # Add variable rules
        for var in sorted_vars:
            name_bytes = var.name.encode("utf-8")
            regex_bytes = _translate_shorthand_classes(var.regex).encode("utf-8")
            self._kept_alive.extend([name_bytes, regex_bytes])
            if not lib.clp_log_mechanic_schema_add_rule(
                self._schema, make_string_view(name_bytes), make_string_view(regex_bytes)
            ):
                msg = f"Failed to add rule '{var.name}' with pattern '{var.regex}'"
                raise RuntimeError(msg)
            self._rule_names.add(var.name)

        # Create lexer from schema
        self._lexer = lib.clp_log_mechanic_lexer_new(self._schema)
        if self._lexer == ffi.NULL:
            msg = "Failed to create Rust lexer (NFA construction failed)"
            raise RuntimeError(msg)

    def __del__(self) -> None:
        self.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def _copy_fragment(self, fragment: object, input_base: int) -> FragmentData:
        """Copy one fragment from the lexer (capture pointers are invalidated on next call)."""
        start_offset = int(ffi.cast("uintptr_t", fragment.start)) - input_base
        end_offset = int(ffi.cast("uintptr_t", fragment.end)) - input_base
        captures: list[tuple[str, str, int, int]] = []
        for i in range(fragment.captures_count):
            cap = fragment.captures[i]
            cap_name = read_string_view(cap.name)
            cap_lexeme = read_string_view(cap.lexeme)
            cap_start = int(ffi.cast("uintptr_t", cap.lexeme.pointer)) - input_base
            cap_end = cap_start + cap.lexeme.length
            if cap_name in self._timestamp_rule_names:
                captures.append(("firstTimestamp", cap_lexeme, cap_start, cap_end))
            elif cap_name in self._rule_names:
                continue
            else:
                captures.append((cap_name, cap_lexeme, cap_start, cap_end))
        return (start_offset, end_offset, bool(fragment.is_event_start), captures)

    def parse(self, text: str) -> Generator[LogEvent, None, None]:
        """Parse text and yield LogEvent objects. Streams one fragment at a time so
        memory stays O(current event) instead of O(entire input)."""
        input_bytes = text.encode("utf-8")
        if not input_bytes:
            yield self._build_event(input_bytes, 0, 0, [])
            return

        input_sv = make_string_view(input_bytes)
        input_buf = ffi.from_buffer("const uint8_t[]", input_bytes)
        input_base = int(ffi.cast("uintptr_t", input_buf))
        pos = ffi.new("size_t *", 0)
        use_timestamp_boundaries = len(self._timestamp_rule_names) > 0

        current_frags: list[FragmentData] = []
        event_start_byte = 0

        while True:
            fragment = lib.clp_log_mechanic_lexer_next_fragment(self._lexer, input_sv, pos)
            if fragment.rule == 0:
                break

            frag_data = self._copy_fragment(fragment, input_base)
            start_offset, end_offset, is_event_start, captures = frag_data

            if use_timestamp_boundaries:
                if is_event_start and current_frags:
                    event_end_byte = self._find_line_start(input_bytes, start_offset)
                    yield self._build_event(
                        input_bytes, event_start_byte, event_end_byte, current_frags
                    )
                    event_start_byte = event_end_byte
                    current_frags = []
            else:
                line_start = self._find_line_start(input_bytes, start_offset)
                if line_start != event_start_byte and current_frags:
                    event_end_byte = line_start
                    yield self._build_event(
                        input_bytes, event_start_byte, event_end_byte, current_frags
                    )
                    event_start_byte = line_start
                    current_frags = []

            current_frags.append((start_offset, end_offset, is_event_start, captures))

        if current_frags:
            yield self._build_event(
                input_bytes, event_start_byte, len(input_bytes), current_frags
            )

    @staticmethod
    def _find_line_start(input_bytes: bytes, offset: int) -> int:
        """Find the start of the line containing the given byte offset."""
        if offset == 0:
            return 0
        # Look backwards for the last newline before offset
        nl_pos = input_bytes.rfind(b"\n", 0, offset)
        if nl_pos == -1:
            return 0
        return nl_pos + 1

    @staticmethod
    def _build_event(
        input_bytes: bytes,
        event_start: int,
        event_end: int,
        fragments: list[FragmentData],
    ) -> LogEvent:
        """Build a LogEvent from a byte range and its fragments."""
        event = LogEvent()
        event._log_message = input_bytes[event_start:event_end].decode("utf-8")  # noqa: SLF001

        log_type_parts: list[str] = []
        var_dict: dict[str, list[str]] = {}
        cursor = event_start  # byte offset cursor (absolute)

        for match_start, match_end, _is_event_start, captures in fragments:
            # Static text before this match
            if match_start > cursor:
                log_type_parts.append(input_bytes[cursor:match_start].decode("utf-8"))

            # Sort captures by start byte offset for correct log type assembly
            sorted_captures = sorted(captures, key=lambda c: c[2])

            inner_cursor = match_start
            for cap_name, cap_value, cap_start, cap_end in sorted_captures:
                # Intra-match static text before this capture
                if cap_start > inner_cursor:
                    log_type_parts.append(input_bytes[inner_cursor:cap_start].decode("utf-8"))
                # C++ backend uses <timestamp> in log type for timestamp captures
                log_type_name = "timestamp" if cap_name == "firstTimestamp" else cap_name
                log_type_parts.append(f"<{log_type_name}>")
                var_dict.setdefault(cap_name, []).append(cap_value)
                inner_cursor = cap_end

            # Trailing intra-match text after last capture
            if inner_cursor < match_end:
                log_type_parts.append(input_bytes[inner_cursor:match_end].decode("utf-8"))

            # Set cursor to end of match (not pos_after which skips the delimiter).
            # The delimiter and any static text between matches will be captured
            # as static text in the next iteration.
            cursor = match_end

        # Trailing static text after last match
        if cursor < event_end:
            log_type_parts.append(input_bytes[cursor:event_end].decode("utf-8"))

        var_dict["@LogType"] = "".join(log_type_parts)  # type: ignore[assignment]
        event._var_dict = var_dict  # noqa: SLF001

        return event

    def close(self) -> None:
        """Release Rust resources. Lexer must be deleted before schema (borrow dependency)."""
        if self._lexer != ffi.NULL:
            lib.clp_log_mechanic_lexer_delete(self._lexer)
            self._lexer = ffi.NULL
        if self._schema != ffi.NULL:
            lib.clp_log_mechanic_schema_delete(self._schema)
            self._schema = ffi.NULL
        self._kept_alive.clear()
