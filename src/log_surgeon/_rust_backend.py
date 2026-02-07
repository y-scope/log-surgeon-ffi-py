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

    def _collect_fragments(
        self,
        input_bytes: bytes,
    ) -> list[FragmentData]:
        """
        Lex all fragments from input, collecting captures for each match.

        Each call to ``next_fragment`` invalidates the previous fragment's
        capture pointers, so we must copy everything eagerly.
        """
        input_sv = make_string_view(input_bytes)
        input_buf = ffi.from_buffer("const uint8_t[]", input_bytes)
        input_base = int(ffi.cast("uintptr_t", input_buf))
        pos = ffi.new("size_t *", 0)

        fragments: list[FragmentData] = []
        while True:
            fragment = lib.clp_log_mechanic_lexer_next_fragment(self._lexer, input_sv, pos)
            if fragment.rule == 0:
                break

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

            fragments.append(
                (
                    start_offset,
                    end_offset,
                    bool(fragment.is_event_start),
                    captures,
                )
            )

        return fragments

    def parse(self, text: str) -> Generator[LogEvent, None, None]:
        """Parse text and yield LogEvent objects."""
        input_bytes = text.encode("utf-8")
        fragments_data = self._collect_fragments(input_bytes)

        # Find event boundary indices (positions where is_event_start == True)
        boundary_indices = [i for i, (_, _, is_start, _) in enumerate(fragments_data) if is_start]

        if not boundary_indices:
            # No timestamp boundaries: split by lines (one event per line),
            # matching the C++ backend behavior.
            yield from self._split_by_lines(input_bytes, fragments_data)
            return

        # Split fragments into groups at boundaries
        groups: list[tuple[int, int, list[FragmentData]]] = []

        # Preamble: any text/fragments before the first timestamp boundary
        first_boundary_match_start = fragments_data[boundary_indices[0]][0]
        first_boundary_line_start = self._find_line_start(input_bytes, first_boundary_match_start)
        if first_boundary_line_start > 0 or boundary_indices[0] > 0:
            preamble_frags = fragments_data[: boundary_indices[0]]
            groups.append((0, first_boundary_line_start, preamble_frags))

        # Each boundary group: from boundary[i] to boundary[i+1] (or end)
        for idx, boundary_pos in enumerate(boundary_indices):
            frag_start = boundary_pos
            frag_end = (
                boundary_indices[idx + 1]
                if idx + 1 < len(boundary_indices)
                else len(fragments_data)
            )
            group_frags = fragments_data[frag_start:frag_end]

            # Event byte range: from the start of the line containing this boundary's
            # match to the start of the line containing the next boundary's match
            # (or end of input for the last group).
            event_start_byte = self._find_line_start(input_bytes, fragments_data[boundary_pos][0])
            if idx + 1 < len(boundary_indices):
                next_boundary_match_start = fragments_data[boundary_indices[idx + 1]][0]
                event_end_byte = self._find_line_start(input_bytes, next_boundary_match_start)
            else:
                event_end_byte = len(input_bytes)

            groups.append((event_start_byte, event_end_byte, group_frags))

        for event_start, event_end, group_frags in groups:
            if not group_frags and event_start == event_end:
                continue
            yield self._build_event(input_bytes, event_start, event_end, group_frags)

    @staticmethod
    def _split_by_lines(
        input_bytes: bytes,
        fragments: list[FragmentData],
    ) -> Generator[LogEvent, None, None]:
        """Split fragments by newlines, yielding one event per line."""
        if not input_bytes:
            yield RustBackend._build_event(input_bytes, 0, 0, [])
            return

        # Find all newline positions to determine line boundaries
        line_starts: list[int] = [0]
        for i, b in enumerate(input_bytes):
            if b == ord("\n"):
                line_starts.append(i + 1)

        # Assign each fragment to the line it starts on
        frag_idx = 0
        for line_idx in range(len(line_starts)):
            line_start = line_starts[line_idx]
            line_end = (
                line_starts[line_idx + 1] if line_idx + 1 < len(line_starts) else len(input_bytes)
            )
            if line_start >= len(input_bytes):
                break

            # Collect fragments whose match_start falls within this line
            line_frags: list[FragmentData] = []
            while frag_idx < len(fragments):
                match_start = fragments[frag_idx][0]
                if match_start >= line_end:
                    break
                line_frags.append(fragments[frag_idx])
                frag_idx += 1

            # Skip blank lines (whitespace-only) that have no matched fragments
            if not line_frags and not input_bytes[line_start:line_end].strip():
                continue
            yield RustBackend._build_event(input_bytes, line_start, line_end, line_frags)

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
