# Development

## Prerequisites

- **Python 3.9+**
- **C++20 compatible compiler**
    - Linux: GCC 10+ or Clang 10+
    - macOS: Xcode 14+ (install with `xcode-select --install`)
- **CMake 3.15+**
    - Linux: `apt install cmake` or `dnf install cmake`
    - macOS: `brew install cmake` or included with Xcode

The Rust toolchain is installed automatically by the build system if not already present.

## Building from source

```bash
# Clone the repository with submodules
git clone --recursive https://github.com/y-scope/log-surgeon-ffi-py.git
cd log-surgeon-ffi-py

# Install taskfile (dependency manager)
sh -c "$(curl -sSL https://taskfile.dev/install.sh)" -- -d
export PATH="$PWD/bin:$PATH"

# Install all dependencies (C++ and Rust)
task deps:install-all

# Install in editable mode for development
pip install -e .
```

`task deps:install-all` handles everything automatically:

- Downloads and builds C++ dependencies (log-surgeon, fmt, Microsoft.GSL)
- Downloads the Rust log-mechanic source
- Installs the Rust nightly toolchain (via rustup) if needed
- Builds `liblog_mechanic.so` (Linux) or `liblog_mechanic.dylib` (macOS)

## Building a wheel

```bash
# Build a wheel for your current Python version
pip wheel . --no-deps -w dist/

# The wheel will be in dist/
ls dist/*.whl
```

The wheel bundles both the C++ extension module and the Rust `liblog_mechanic` shared library.
No extra installation steps or environment variables are needed by end users.

To build wheels matching CI output (using cibuildwheel):

```bash
# Install cibuildwheel
pip install cibuildwheel

# Build for a specific Python version (e.g., Python 3.12)
# Linux: cp312-manylinux_x86_64
# macOS: cp312-macosx_universal2
cibuildwheel --only cp312-macosx_universal2

# Wheels will be in wheelhouse/
ls wheelhouse/*.whl
```

## Running tests

```bash
# Install test dependencies
pip install pytest

# Run all tests with the default (C++) backend
python -m pytest tests/

# Run all tests with the Rust backend
LOG_SURGEON_BACKEND=rust python -m pytest tests/
```

## Rust backend

The Rust backend (`liblog_mechanic`) is built and bundled automatically by the build system.
When installed from a wheel, no additional setup is required.

### Using the Rust backend

```python
# Via constructor parameter
parser = Parser(backend="rust")

# Via environment variable (applies to all Parser instances)
# export LOG_SURGEON_BACKEND=rust
parser = Parser()
```

### Development: overriding the library path

During development, if you want to use a locally built version of `liblog_mechanic` instead of
the bundled one, set the `LOG_MECHANIC_LIB_PATH` environment variable:

```bash
export LOG_MECHANIC_LIB_PATH=/path/to/log-surgeon/rust/target/release/liblog_mechanic.so
```

The library discovery order is:

1. `LOG_MECHANIC_LIB_PATH` env var (exact path override)
2. Bundled in the installed package directory (wheel installs)
3. Project layout fallbacks (submodule, sibling repo, cwd — for editable installs)

### Running Rust-side tests

```bash
cd log-surgeon/rust
cargo test
```

## Linting and type checking

```bash
# Install dev dependencies
pip install ruff mypy

# Run linter
ruff check src/

# Run type checker
mypy src/
```
