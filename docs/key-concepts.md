# Key Concepts

This document covers concepts specific to `log-surgeon` and its Python bindings. For standard regex syntax (quantifiers, character classes, etc.), see [regex101.com](https://regex101.com/) or the [Python re module documentation](https://docs.python.org/3/library/re.html).

---

## log-surgeon Specific Concepts

These behaviors are unique to log-surgeon and differ from standard regex engines.

### Delimiter-based matching

**This is the most important difference from traditional regex.**

In log-surgeon, the `.` wildcard matches any character **except delimiters**. This differs from standard regex where `.` matches any character except newline.

Default delimiters include whitespace (space, tab, newline) and common punctuation like `:`, `,`, `/`, `(`, `)`, etc. This is an illustrative subset—see the source code for the complete list.

```python
from log_surgeon import Parser

parser = Parser()  # Default delimiters include space
parser.add_var("token", rf"(?<match>d.*)")
parser.compile()

event = parser.parse_event("abc def ghi")
print(event['match'])  # Output: "def" (NOT "def ghi")
```

**Why?** Because `.*` stops at the space delimiter. To match across delimiters, use character classes that explicitly include them:

```python
# Include space in the character class to match across it
parser.add_var("multi", rf"(?<match>d[a-z ]*i)")  # Matches "def ghi"
```

You can customize delimiters when creating a Parser:

```python
parser = Parser(delimiters=r" \t\n,:")  # Custom delimiter set
```

For more details on log-surgeon's schema format and delimiter behavior, see the [log-surgeon documentation](https://github.com/y-scope/log-surgeon).

### Variable priority and ordering

Variables are matched in schema order. Use the `priority` parameter to control ordering:

```python
from log_surgeon import Parser, PATTERN

parser = Parser()

# High priority (5) - specific patterns match first
parser.add_var("ip_address", rf"(?<ip>{PATTERN.IPV4})", priority=5)

# Default priority (0) - normal patterns
parser.add_var("user_id", rf"user=(?<user>[a-zA-Z0-9]+)")

# Low priority (-1, -2) - generic fallbacks match last
parser.add_var("generic_int", rf"(?<int>\d+)", priority=-2)

parser.compile()
```

**Rules:**
- Higher values appear first in schema (higher precedence).
- Default priority is 0.
- Same priority maintains insertion order.
- Timestamps (via `add_timestamp()`) always appear first, regardless of priority.

### Named capture groups

Use `(?<name>pattern)` syntax to extract fields:

```python
parser.add_var("metric", rf"metric=(?<metric_name>[a-zA-Z0-9_]+) value=(?<value>\d+)")

event = parser.parse_event("metric=cpu value=42")
print(event['metric_name'])  # "cpu"
print(event['value'])        # "42"
```

### Schema format

The compiled schema defines delimiters, timestamps, and variables:

```
delimiters: \t\r\n:,!;%@/()[]
timestamp:<timestamp_regex>
variable_name:<variable_regex>
```

When using the fluent API (`Parser.add_var()` and `Parser.compile()`), the schema is built automatically.

---

## Python Layer Concepts

These are specific to the Python bindings.

### Using raw f-strings for regex patterns

**Strongly recommended:** Use raw f-strings (`rf"..."`) for all regex patterns.

```python
# Without raw strings - requires double-escaping (error-prone)
parser.add_var("metric", "value=(\\d+)")

# With raw f-strings - clean and readable
parser.add_var("metric", rf"value=(?<value>\d+)")
```

Raw f-strings combine:
- **Raw strings (`r"..."`)**: No double-escaping for `\d`, `\w`, etc.
- **f-strings (`f"..."`)**: Easy interpolation of PATTERN constants.

**Watch out for braces:** In f-strings, literal `{` and `}` must be doubled:

```python
parser.add_var("json", rf"data={{(?<content>[^}}]+)}}")  # Matches: data={...}
```

### PATTERN constants

Pre-built patterns for common log elements. See [API Reference](api-reference.md#pattern) for the full list.

```python
from log_surgeon import Parser, PATTERN

parser = Parser()
parser.add_var("network", rf"(?<ip>{PATTERN.IPV4}):(?<port>{PATTERN.PORT})")
parser.add_var("metrics", rf"value=(?<val>{PATTERN.FLOAT})")
parser.compile()
```

### Backend selection

`log-surgeon-ffi` supports two backend engines: C++ (default) and Rust. Both are bundled in
the wheel and require no extra installation. Select via the `backend` parameter or the
`LOG_SURGEON_BACKEND` environment variable:

```python
# Via parameter
parser = Parser(backend="rust")

# Via environment variable (default: "cpp")
# export LOG_SURGEON_BACKEND=rust
parser = Parser()
```

Both backends share the same Python API. The Rust backend is under active development and
may have minor behavioral differences noted below.

### Supported regex syntax

log-surgeon uses its own regex dialect, which is a subset of standard regex. The supported
escape sequences differ between backends:

| Escape | Meaning | C++ | Rust |
|--------|---------|-----|------|
| `\d` | `[0-9]` | Native | Translated in Python |
| `\s` | `[ \t\r\n]` | Native | Translated in Python |
| `\w` | `[a-zA-Z0-9_]` | **Not supported** | Translated in Python |
| `\n` `\r` `\t` | Newline, carriage return, tab | Native | Native |

!!! tip
    For maximum portability across backends, use explicit character classes:
    `[0-9]` instead of `\d`, `[a-zA-Z0-9_]` instead of `\w`.

The Rust backend automatically translates `\d`, `\w`, and `\s` (and their negated uppercase
forms `\D`, `\W`, `\S`) to their equivalent character classes before passing patterns to the
engine.

Features **not supported** by either backend: lookahead, lookbehind, backreferences, `\b`
(word boundaries), non-greedy quantifiers (`*?`, `+?`).

---

## Common Pitfalls

**Pattern matches less than expected**
- You're likely using `.*` which stops at delimiters. Use explicit character classes like `[a-zA-Z ]*` to include delimiters you want to match across.

**Pattern works in regex101 but not here**
- log-surgeon's `.` excludes delimiters; standard regex's `.` only excludes newline. This is the most common source of confusion.

**Escape sequence errors**
- Use raw f-strings (`rf"..."`) instead of regular strings to avoid double-escaping issues.

**`\w` crashes the C++ backend**
- The C++ backend does not support `\w`. Use `[a-zA-Z0-9_]` instead for cross-backend compatibility. The Rust backend translates `\w` automatically.
