# pr-size-guard

[![PyPI version](https://img.shields.io/pypi/v/trysac-pr-size-guard)](https://pypi.org/project/trysac-pr-size-guard/)
[![License: MIT](https://img.shields.io/pypi/l/trysac-pr-size-guard)](LICENSE)
[![CI](https://github.com/Trysac/u272-pr-size-guard/actions/workflows/ci.yml/badge.svg)](https://github.com/Trysac/u272-pr-size-guard/actions/workflows/ci.yml)

Measure pull request size from git numstat or unified diffs, ignore lock and generated files, flag warn and fail thresholds and suggest how to split the change into reviewable slices

## Problem

Describe in two or three sentences the concrete problem this utility solves, who hits it, and what
they do today without it. Replace this paragraph when the first real feature lands.

## Install

```sh
pip install trysac-pr-size-guard
# or
uv add trysac-pr-size-guard
```

Requires Python 3.10 or newer. No runtime dependencies.

## Usage

```python
import pr_size_guard

# normalize() trims surrounding whitespace and lower-cases the text.
print(pr_size_guard.normalize("  Hello World "))  # -> "hello world"

# Blank input is rejected explicitly instead of returning an empty string.
try:
    pr_size_guard.normalize("   ")
except ValueError as exc:
    print(f"rejected: {exc}")
```

## Documentation

- [Architecture](docs/ARCHITECTURE.md) and [decisions](docs/decisions/)
- [Testing](docs/TESTING.md) and [security](docs/SECURITY.md)
- [Project record](docs/PROJECT.md) and [stack](docs/STACK.md)
- [Changelog](CHANGELOG.md) and [contributing guide](CONTRIBUTING.md)

## License

[MIT](LICENSE) (c) 2026 Miguel Gomez
