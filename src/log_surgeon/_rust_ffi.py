"""Low-level cffi ABI-mode bindings for the Rust log-mechanic shared library."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import cffi

ffi = cffi.FFI()
ffi.cdef("""
    typedef struct { const char *pointer; size_t length; } CStringView;
    typedef struct { CStringView name; CStringView lexeme; } CCapture;
    typedef struct {
        size_t rule;
        const uint8_t *start;
        const uint8_t *end;
        const CCapture *captures;
        size_t captures_count;
        bool is_event_start;
    } CLogFragment;

    typedef struct Schema Schema;
    typedef struct Lexer Lexer;

    void clp_log_mechanic_set_debug(bool enable);

    Schema *clp_log_mechanic_schema_new(void);
    void clp_log_mechanic_schema_delete(Schema *schema);
    bool clp_log_mechanic_schema_set_delimiters(Schema *schema, CStringView delimiters);
    bool clp_log_mechanic_schema_add_rule(
        Schema *schema, CStringView name, CStringView pattern);
    bool clp_log_mechanic_schema_add_timestamp_rule(
        Schema *schema, CStringView name, CStringView pattern);
    size_t clp_log_mechanic_schema_rule_count(const Schema *schema);
    CStringView clp_log_mechanic_schema_rule_name(const Schema *schema, size_t index);

    Lexer *clp_log_mechanic_lexer_new(const Schema *schema);
    void clp_log_mechanic_lexer_delete(Lexer *lexer);
    CLogFragment clp_log_mechanic_lexer_next_fragment(Lexer *lexer, CStringView input, size_t *pos);
""")


def _find_library() -> str:
    """
    Find the log-mechanic shared library.

    Search order:
    1. ``LOG_MECHANIC_LIB_PATH`` env var (exact path override).
    2. Package directory (bundled in wheel via CMake install).
    3. Project layout fallbacks for development (submodule, sibling, cwd).
    """
    env_path = os.environ.get("LOG_MECHANIC_LIB_PATH")
    if env_path:
        return env_path

    if sys.platform == "darwin":
        lib_name = "liblog_mechanic.dylib"
    else:
        lib_name = "liblog_mechanic.so"

    # Bundled in wheel: the .so is installed alongside this Python file
    package_dir = Path(__file__).resolve().parent
    bundled = package_dir / lib_name
    if bundled.exists():
        return str(bundled)

    # Development fallbacks — search common project layouts (release preferred over debug).
    # project_root is two parents up from package_dir (the src layout).
    # Checks submodule, sibling, and CWD-based Cargo target directories.
    project_root = package_dir.parent.parent
    search_dirs: list[Path] = []
    for base in [
        project_root / "lib" / "log-surgeon",
        project_root.parent / "log-surgeon",
        Path.cwd(),
    ]:
        search_dirs.append(base / "rust" / "target" / "release")
        search_dirs.append(base / "rust" / "target" / "debug")

    for d in search_dirs:
        candidate = d / lib_name
        if candidate.exists():
            return str(candidate)

    msg = (
        f"Could not find {lib_name}. Set LOG_MECHANIC_LIB_PATH or build "
        f"the Rust library with: cd log-surgeon/rust && cargo build --release"
    )
    raise FileNotFoundError(msg)


lib = ffi.dlopen(_find_library())


def make_string_view(b: bytes) -> cffi.FFI.CData:
    """
    Create a CStringView from a bytes object.

    The caller must keep the bytes object alive for the lifetime of the view.
    """
    sv = ffi.new("CStringView *")
    sv.pointer = ffi.from_buffer("const char[]", b)
    sv.length = len(b)
    return sv[0]


def read_string_view(sv: cffi.FFI.CData) -> str:
    """Read a CStringView into a Python str."""
    return ffi.unpack(sv.pointer, sv.length).decode("utf-8")
