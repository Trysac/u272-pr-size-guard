# Stack

## Used

The implementation uses the Python standard library only; there are no runtime dependencies.

| Area | Used in code |
|---|---|
| Python 3.10+ | Type syntax such as `str | None`, `tuple[str, ...]`, and `list[FileChange]`. |
| `argparse` | CLI parsing in `src/pr_size_guard/__main__.py`. |
| `dataclasses` | Frozen `FileChange`, `Assessment`, and `Slice` value objects. |
| `fnmatch` | Basename matching for ignore patterns without `/`. |
| `logging` | Module logger with a `NullHandler`. |
| `re` | Fixed-pattern rename cleanup in `_resolve_rename`. |
| `typing` | `Literal` annotations for status and error code. |
| `pytest` | Tests in `tests/test_pr_size_guard.py`. |

## Discarded

No discarded alternatives are recorded in the code or specification for this snapshot. The library does not call git or the GitHub API and does not require a third-party runtime package.
