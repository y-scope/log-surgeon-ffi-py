#!/usr/bin/env python3
"""Generate README.md from README.md.in template using config from pyproject.toml."""

from pathlib import Path

try:
    import tomllib
except ImportError:
    import tomli as tomllib  # type: ignore[import-not-found,no-redef]


def main() -> None:
    project_root = Path(__file__).parent.parent

    # Read config from pyproject.toml
    pyproject_path = project_root / "pyproject.toml"
    with pyproject_path.open("rb") as f:
        config = tomllib.load(f)

    docs_version = config["tool"]["log-surgeon"]["docs_version"]

    # Read template
    template_path = project_root / "README.md.in"
    template = template_path.read_text()

    # Substitute placeholder
    readme_content = template.replace("{{DOCS_VERSION}}", docs_version)

    # Write output
    readme_path = project_root / "README.md"
    readme_path.write_text(readme_content)

    print(f"Generated README.md with docs_version={docs_version}")


if __name__ == "__main__":
    main()
