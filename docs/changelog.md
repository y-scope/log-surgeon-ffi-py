# Changelog

All notable changes to `log-surgeon-ffi` are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [0.1.0-beta.10]

### Added

- **Rust backend.** C++ remains the default; Rust backend is available via `Parser(backend="rust")` or the `LOG_SURGEON_BACKEND=rust` environment variable. The `liblog_mechanic` shared library is compiled during the wheel build and installed inside the `log_surgeon/` package directory, so no manual build or `LOG_MECHANIC_LIB_PATH` is required.
- **`cffi` is now a required dependency** (previously optional under `[rust]` extra). Rust backend is available out of the box.
- **`RustBackend` context manager.** Resources are released automatically when using `with` statement.
- **Build: Rust in wheels.** `taskfiles/deps.yaml` adds `log-mechanic` and `log-mechanic-build` tasks (download Rust source, install toolchain via rustup if needed, build with platform-aware logic: Linux glibc/musl, macOS universal2). `CMakeLists.txt` installs the built `.so`/`.dylib` into the package directory. CI installs Rust toolchain on macOS runners and in Linux containers.
- **`"Programming Language :: Rust"` classifier** in `pyproject.toml`.
- **Backend performance tests** (`tests/test_backend_performance.py`). Compare C++ vs Rust throughput: `parse_event` (duration-based) and `parse` stream (fixed iterations). Optional RSS monitoring to stop early if memory grows. Correctness checks ensure both backends produce equivalent results.
- **Documentation: why C++ is faster in benchmarks.** README and Architecture doc describe the top two reasons: (1) C++ does full parse and event assembly in native code and returns one event per call; Rust exposes a fragment-level lexer and event assembly is done in Python. (2) Rust incurs more FFI round-trips per event than C++ (one call per event).

### Changed

- **Rust backend: streaming parse.** `RustBackend.parse()` now streams one fragment at a time instead of collecting all fragments for the entire input before yielding events. Memory usage is O(current event) instead of O(entire input), so long-running or repeated parsing no longer grows unbounded.
- **`pyproject.toml`: `before-build` replaced with `before-all`.** C++ and Rust dependencies build once per platform container instead of once per Python version.
- **`_rust_ffi.py`: library discovery.** Search order is (1) `LOG_MECHANIC_LIB_PATH` env var, (2) package directory (bundled in wheel), (3) project layout fallbacks for development.

### Removed

- **`[project.optional-dependencies] rust` extra.** `cffi` is now a required dependency; `pip install log-surgeon-ffi[rust]` is no longer needed.

