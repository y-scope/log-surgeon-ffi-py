# Changelog

All notable changes to `log-surgeon-ffi` are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [Unreleased]

### Added

- **Rust backend bundled in wheels.** The `liblog_mechanic` shared library is now compiled from
  source during the wheel build and installed inside the `log_surgeon/` package directory. Users
  no longer need to build the Rust library manually or set `LOG_MECHANIC_LIB_PATH`. Switching to
  the Rust backend is as simple as `Parser(backend="rust")`.
- **`cffi` is now a required dependency** (previously optional under `[rust]` extra). This ensures
  the Rust backend is available out of the box.
- **`RustBackend` supports the context manager protocol** (`with` statement). Resources are
  released automatically on exit.
- **`taskfiles/deps.yaml`: `log-mechanic` and `log-mechanic-build` tasks.** The build system
  downloads the Rust source, installs the Rust toolchain (via rustup) if needed, and builds
  `liblog_mechanic` with platform-aware logic:
    - Linux glibc: native `cargo build --release`
    - Linux musl: cross-compiled with the appropriate musl target
    - macOS: universal2 fat binary via `lipo` (arm64 + x86_64)
- **`CMakeLists.txt`: Rust library install rule.** The built `.so`/`.dylib` is installed into the
  `log_surgeon/` package directory inside the wheel.
- **CI: Rust toolchain on macOS runners.** The GitHub Actions workflow installs Rust on macOS
  before `cibuildwheel` runs. Linux builds install Rust inside the container via the taskfile.
- **`"Programming Language :: Rust"` classifier** added to `pyproject.toml`.

### Changed

- **`pyproject.toml`: `before-build` replaced with `before-all`.** Dependencies (both C++ and
  Rust) are Python-version-independent and now build once per platform container instead of once
  per Python version.
- **`_rust_ffi.py`: library discovery prioritizes bundled library.** Search order is now:
  (1) `LOG_MECHANIC_LIB_PATH` env var, (2) package directory (bundled in wheel),
  (3) project layout fallbacks (dev mode).
- **`_rust_backend.py`: merged duplicate `TYPE_CHECKING` import blocks.**

### Removed

- **`[project.optional-dependencies] rust` extra.** The `cffi` dependency moved to required
  dependencies, so `pip install log-surgeon-ffi[rust]` is no longer needed.

---

## [0.1.0-beta.9]

Initial beta release with C++ and Rust backend support.

- C++ backend via pybind11 extension module (default)
- Rust backend via cffi/dlopen (requires manual library build)
- Parser, JsonParser, Query API
- PATTERN constants for common log elements
- pandas DataFrame and PyArrow Table export
- Multi-line event support (timestamps, stack traces)
