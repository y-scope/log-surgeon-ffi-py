# Key Concepts

> **CRITICAL: You must understand these concepts to use `log-surgeon` correctly.**
>
> `log-surgeon` works **fundamentally differently** from traditional regex engines like Python's
> `re` module, PCRE, or JavaScript regex. Skipping this section may lead to patterns that don't
> work as expected.

## Delimiter-based matching

**CRITICAL:** In `log-surgeon`, the `.` wildcard matches any character **except delimiters**. This is
fundamentally different from traditional regex engines where `.` matches any character except newline.
This single difference affects how many patterns behave.

### How delimiters work

Delimiters are characters that define boundaries in log messages. The default delimiters include:
- Whitespace: space, tab (`\t`), newline (`\n`), carriage return (`\r`)
- Punctuation: `:`, `,`, `!`, `;`, `%`, `@`, `/`, `(`, `)`, `[`, `]`

For example, with default delimiters, the log message `"abc def ghi"` has spaces as delimiter
boundaries, separating `"abc"`, `"def"`, and `"ghi"`.

You can customize delimiters when creating a Parser:

```python
parser = Parser(delimiters=r" \t\n,:")  # Custom delimiters (no escaping needed for special chars)
```

### How `.` behaves differently

**Critical:** Since `.` doesn't match delimiter characters, patterns like `.*` stop at delimiters.

```python
from log_surgeon import Parser

parser = Parser()  # Default delimiters include space
parser.add_var("token", rf"(?<match>d.*)")
parser.compile()

event = parser.parse_event("abc def ghi")

# Matches only "def" because .* stops at the space delimiter
# Does NOT match "def ghi"
print(event['match'])  # Output: "def"
```

**In a traditional regex engine**, `d.*` would match `"def ghi"` (everything from 'd' to end).
**In log-surgeon**, `d.*` matches only `"def"` because `.` doesn't match the space character.

### Why delimiter-based?

Delimiter-based matching enables:
- **Faster parsing** by using delimiters as natural boundaries
- **Predictable behavior** aligned with log structure
- **Efficient log type generation** for analytics

### Matching across delimiters

To match text that contains delimiters, use **character classes** that explicitly include the delimiter:

```python
from log_surgeon import Parser

parser = Parser()  # Default delimiters include space

#  Using .* - stops at delimiter
parser.add_var("wrong", rf"(?<match>d.*)")  # Matches only "def"

#  Using character class that includes space - matches across delimiter
parser.add_var("correct", rf"(?<match>d[a-z ]*i)")  # Matches "def ghi"
parser.compile()

event = parser.parse_event("abc def ghi")
print(event['match'])  # Output: "def ghi"
```

**Key Rule:** Character classes like `[a-zA-Z]*`, `[a-z ]*`, or `[\w\s]*` can match delimiters if
they include them, but `.*` cannot (since `.` excludes delimiters).

### Alternation

Alternation (`|`) works as expected in log-surgeon, with concatenation binding more tightly than alternation (standard regex precedence).

```python
from log_surgeon import Parser

parser = Parser()

# Alternation works as expected: matches "abc" OR "def"
parser.add_var("word", rf"(?<word>abc|def)")

# Log levels: matches "ERROR" OR "WARN" OR "INFO"
parser.add_var("level", rf"(?<level>ERROR|WARN|INFO)")

# Status values: matches "success" OR "failure"
parser.add_var("status", rf"(?<status>success|failure)")

parser.compile()
```

You can use parentheses for grouping when needed:

```python
# Optional prefix with alternation
parser.add_var("msg", rf"(?<msg>(error|warn): .+)")

# Complex patterns
parser.add_var("id", rf"(?<id>(user|admin)_\d+)")
```

### Optional patterns and quantifiers

log-surgeon supports standard regex quantifiers:

| Quantifier | Meaning |
|------------|---------|
| `?` | 0 or 1 (optional) |
| `*` | 0 or more |
| `+` | 1 or more |
| `{n}` | Exactly n |
| `{n,m}` | Between n and m |

```python
from log_surgeon import Parser

parser = Parser()

#  Use ? for optional patterns (matches 0 or 1)
parser.add_var("optional1", rf"(?<level>ERROR|WARN)?")  # Matches 0 or 1 occurrence

#  {0,1} is equivalent to ?
parser.add_var("optional2", rf"(?<level>ERROR|WARN){0,1}")  # Also matches 0 or 1 occurrence

#  Use * for 0 or more occurrences
parser.add_var("digits", rf"(?<num>\d*)")  # Matches 0 or more digits

#  Use + for 1 or more occurrences
parser.add_var("word", rf"(?<word>\w+)")  # Matches 1 or more word characters
parser.compile()
```

**Best practice:** Use `?` or `{0,1}` for optional elements (0 or 1 occurrences). Use `*` for 0 or more, and `+` for 1 or more.

### Regex shorthands

log-surgeon supports common regex character class shorthands:

| Shorthand | Meaning | Equivalent |
|-----------|---------|------------|
| `\d` | Digit | `[0-9]` |
| `\D` | Non-digit | `[^0-9]` |
| `\s` | Whitespace | `[ \t\n\r\v\f]` |
| `\S` | Non-whitespace | `[^ \t\n\r\v\f]` |
| `\w` | Word character | `[a-zA-Z0-9_]` |
| `\W` | Non-word character | `[^a-zA-Z0-9_]` |

```python
from log_surgeon import Parser

parser = Parser()

# Using shorthands for cleaner patterns
parser.add_var("number", rf"(?<num>\d+)")           # Matches digits
parser.add_var("word", rf"(?<word>\w+)")            # Matches word characters
parser.add_var("trimmed", rf"(?<text>\S+)")         # Matches non-whitespace

parser.compile()
```

These shorthands can be used standalone, in character classes, or combined with quantifiers:

```python
# In character classes
parser.add_var("alphanumeric", rf"(?<id>[\w-]+)")   # Word chars + hyphen

# Combined with quantifiers
parser.add_var("optional_num", rf"(?<num>\d+)?")    # Optional digits
```

You can also explicitly include delimiters in your pattern:

```python
# To match "def ghi", explicitly include the space delimiter in your pattern
parser.add_var("multi", rf"(?<match>d\w+\s+\w+)")
# \s matches whitespace, so this pattern can span the space
```

Or adjust your delimiters to change what `.` can match:

```python
# Use only newline as delimiter, so . matches spaces, colons, etc.
parser = Parser(delimiters=r"\n")
```

## Named capture groups

Use named capture groups in regex patterns to extract specific fields:

```python
parser.add_var("metric", rf"metric=(?<metric_name>\w+) value=(?<value>\d+)")
```

The syntax `(?<name>pattern)` creates a capture group that can be accessed as `event['name']`.

**Note:** See [Using Raw f-strings](#using-raw-f-strings-for-regex-patterns) for best practices on
writing regex patterns.

## Variable priority and ordering

Variable order in the schema determines matching precedence. Variables that appear first in the schema take precedence over those that appear later. Use the `priority` parameter to control this ordering:

> **Note:** Timestamps added via `add_timestamp()` always appear first in the schema and cannot be reordered with priority. Priority only controls the ordering of variables added via `add_var()`.

```python
from log_surgeon import Parser, PATTERN

parser = Parser()

# Timestamps are always first (added via add_timestamp)
parser.add_timestamp("ts", r"\d{4}/\d{2}/\d{2} \d{2}:\d{2}:\d{2}")

# High priority - specific patterns should match first
parser.add_var("ip_address", rf"(?<ip>{PATTERN.IPV4})", priority=5)
parser.add_var("specific_id", rf"ID(?<id>\d{{6}})", priority=5)

# Default priority (0) - normal patterns
parser.add_var("user_id", rf"user=(?<user>[a-zA-Z0-9]+)")
parser.add_var("status", rf"status=(?<status>[a-z]+)")

# Low priority (negative) - generic fallback patterns
parser.add_var("generic_float", rf"(?<float>{PATTERN.FLOAT})", priority=-1)
parser.add_var("generic_int", rf"(?<int>\d+)", priority=-2)

parser.compile()
```

**How priority works:**
- **Higher values appear first** in the schema (higher = higher precedence)
- **Default priority is 0** for normal patterns
- **Negative values** for generic/fallback patterns (more negative = lower priority)
- **Same priority** variables maintain insertion order

**Example ordering in compiled schema:**
```
[Timestamps always first - added via add_timestamp()]
priority=5:   ip_address, specific_id (insertion order)
priority=0:   user_id, status (insertion order)
priority=-1:  generic_float
priority=-2:  generic_int (matches last)
```

**Why this matters:** Without priority control, a generic `\d+` pattern added first could match "192" or specific IDs before your specific patterns get a chance. With priorities, you ensure specific patterns try to match before generic ones.

**Important:** Timestamps (added with `add_timestamp()`) are special anchoring patterns that always appear first in the schema, regardless of priority values.

## Using raw f-strings for regex patterns

> **⚠️ STRONGLY RECOMMENDED: Use raw f-strings (`rf"..."`) for all regex patterns.**
>
> While not absolutely required, using regular strings will likely cause escaping issues and pattern
failures. Raw f-strings prevent these problems.

Raw f-strings combine the benefits of:
- **Raw strings (`r"..."`)**: No need to double-escape regex special characters like `\d`, `\w`,
  `\n`
- **f-strings (`f"..."`)**: Easy interpolation of variables and pattern constants

### Why use raw f-strings?

```python
#  Without raw strings - requires double-escaping
parser.add_var("metric", "value=(\\d+)")  # Hard to read, error-prone

#  With raw f-strings - single escaping, clean and readable
parser.add_var("metric", rf"value=(?<value>\d+)")
```

### Watch out for braces in f-strings

When using f-strings, literal `{` and `}` characters must be escaped by doubling them:

```python
from log_surgeon import Parser, Pattern

parser = Parser()

#  Correct: Escape literal braces in regex
parser.add_var("json", rf"data={{(?<content>[^}}]+)}}")  # Matches: data={...}
parser.add_var("range", rf"range={{(?<min>\d+),(?<max>\d+)}}")  # Matches: range={10,20}

#  Using Pattern constants with interpolation
parser.add_var("ip", rf"IP: (?<ip>{Pattern.IPV4})")
parser.add_var("float", rf"value=(?<val>{Pattern.FLOAT})")

#  Common regex patterns
parser.add_var("digits", rf"\d+ items")  # No double-escaping needed
parser.add_var("word", rf"name=(?<name>\w+)")
parser.add_var("whitespace", rf"split\s+by\s+spaces")

parser.compile()
```

### Examples: raw f-strings vs regular strings

```python
# Regular string - requires double-escaping
parser.add_var("path", "path=(?<path>\\w+/\\w+)")  # Hard to read

# Raw f-string - natural regex syntax
parser.add_var("path", rf"path=(?<path>\w+/\w+)")  # Clean and readable

# With interpolation
log_level = "INFO|WARN|ERROR"
parser.add_var("level", rf"(?<level>{log_level})")  # Easy to compose
```

**Recommendation:** Consistently use `rf"..."` for all regex patterns. This approach:
- Avoids double-escaping mistakes that break patterns
- Makes patterns more readable
- Allows easy use of Pattern constants and variables
- Only requires watching for literal braces `{` and `}` in f-strings (escape as `{{` and `}}`)

Using regular strings (`"..."`) will require double-escaping (e.g., `"\\d+"`) which is error-prone
and can be hard to read.

## Schema Format

The schema defines delimiters, timestamps, and variables for parsing:

```
// schema delimiters
delimiters: \t\r\n:,!;%@/()[]

// schema timestamps
timestamp:<timestamp_regex>

// schema variables
variable_name:<variable_regex>
```

When using the fluent API (`Parser.add_var()` and `Parser.compile()`), the schema is built automatically.

## Common Pitfalls

 **Pattern doesn't match anything**
- Check: Are you using `.*` to match across delimiters? Use `[a-zA-Z ]*` instead
- Check: Did you forget to call `parser.compile()`?
- Check: Are your delimiters causing `.` to stop matching unexpectedly?

 **Pattern works in regex tester but not here**
- Remember: In log-surgeon, `.` matches any character **except delimiters**
- Traditional regex engines: `.` matches any character except newline
- This means `.*` stops at spaces, colons, etc. in log-surgeon
- Read: [Delimiter-based matching](#delimiter-based-matching)

 **Escape sequence errors in Python**
- Problem: `parser.add_var("digits", "(?<num>\d+)")` raises SyntaxError
- Solution: Use `rf"..."` (raw f-string) instead of `"..."` or `f"..."`
- Example: `parser.add_var("digits", rf"(?<num>\d+)")`

 **Optional patterns and quantifiers**
- `?` matches 0 or 1 occurrences (equivalent to `{0,1}`)
- `*` matches 0 or more occurrences
- `+` matches 1 or more occurrences
- Example: `(?<level>ERROR|WARN)?` for optional log level
