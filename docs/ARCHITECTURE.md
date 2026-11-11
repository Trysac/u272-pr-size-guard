# Architecture

## Purpose

`pr_size_guard` measures reviewable pull request size from `git diff --numstat` or unified diff text. It parses changes, applies ignore patterns, evaluates warn/fail thresholds, and suggests directory-based slices. The library uses only the Python standard library.

## Shape

```text
src/pr_size_guard/__init__.py  public API, parsing, assessment, slicing
src/pr_size_guard/__main__.py  argparse CLI (--numstat/--diff, thresholds, --suggest)
tests/test_pr_size_guard.py   pytest tests for the public API
```

- Public API: names in `__all__`: `DEFAULT_IGNORE`, `Assessment`, `FileChange`, `PrSizeError`, `Slice`, `assess`, `parse_numstat`, `parse_unified_diff`, `suggest_slices`. `FileChange.lines` is a property.
- `FileChange` stores `path`, `added`, `deleted`, `binary`. Parsers return lists of these; `assess` and `suggest_slices` consume any iterable of them.
- Errors: all library errors are `PrSizeError` with a `code` of `parse_error`, `input_too_large`, `invalid_pattern`, or `invalid_options`, and an optional message. The library never prints or exits. The CLI prints and maps errors to exit code 2.
- Side effects: library functions have no I/O. The CLI reads one file or stdin and writes to stdout/stderr.
- Limit: both parsers reject input longer than `MAX_INPUT_LENGTH = 52_428_800` characters.

## Quality contract

The code snapshot has no `scripts/check.py` or factory gate file. The test module is `tests/test_pr_size_guard.py`; it checks the public API, parser edge cases, error codes, logger setup, and the `assess` acceptance case. See [TESTING.md](TESTING.md).

## Decisions

No numbered ADRs or `decisions/` directory are present in this code snapshot.
