# Development

## Prerequisites

- **Python 3.9+**
- **C++20 compatible compiler**
  - Linux: GCC 10+ or Clang 10+
  - macOS: Xcode 14+ (install with `xcode-select --install`)
- **CMake 3.15+**
  - Linux: `apt install cmake` or `dnf install cmake`
  - macOS: `brew install cmake` or included with Xcode

## Building from source

```bash
# Clone the repository with submodules
git clone --recursive https://github.com/y-scope/log-surgeon-ffi-py.git
cd log-surgeon-ffi-py

# Install taskfile (dependency manager)
sh -c "$(curl -sSL https://taskfile.dev/install.sh)" -- -d
export PATH="$PWD/bin:$PATH"

# Install C++ dependencies (log-surgeon, fmt, Microsoft.GSL)
task deps:install-all

# Install in editable mode for development
pip install -e .
```

## Building a wheel

```bash
# Build a wheel for your current Python version
pip wheel . --no-deps -w dist/

# The wheel will be in dist/
ls dist/*.whl
```

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

# Run tests
python -m pytest tests/
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
