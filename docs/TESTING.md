# Testing

## Running

```sh
PYTHONPATH=src python -m pytest tests/test_pr_size_guard.py
```

The tests import the public API directly from `pr_size_guard`; they do not require network access or external tools.

## Policy

- `tests/test_pr_size_guard.py` is the test module in this snapshot.
- Tests assert exact `FileChange`, `Assessment`, and `Slice` values, `PrSizeError.code`, logger handlers, and parser behavior.
- The compiled test module shows input-size tests use `monkeypatch.setattr(pr_size_guard, "MAX_INPUT_LENGTH", ...)`, so they do not allocate 50 MiB strings.
- No coverage threshold or CI gate file is present in this snapshot.

## Tiers

The repository contains one local pytest tier. No `@pytest.mark.conformance` tests, external tool setup, or CI-specific deselection are present in the compiled test module.

## Layout

`tests/test_pr_size_guard.py` is the only test file in the snapshot. No shared `tests/conftest.py` is present in this snapshot.

## Test files

`tests/test_pr_size_guard.py` contains tests for:

- `FileChange.lines` and frozen dataclass behavior (`test_file_change_lines_and_frozen`).
- `PrSizeError.code` (`test_pr_size_error_code`).
- The module logger having a `NullHandler` (`test_logger_has_null_handler`).
- Numstat parsing: acceptance input (`test_parse_numstat_acceptance`), paths with spaces (`test_parse_numstat_basic_and_spaces`), whole-path renames (`test_parse_numstat_rename_whole_path`), duplicate-slash collapse (`test_parse_numstat_duplicate_slash_collapse`), invalid lines (`test_parse_numstat_invalid_line`), non-integer counts (`test_parse_numstat_invalid_counts`), negative counts (`test_parse_numstat_negative_counts`), blank lines (`test_parse_numstat_skips_blank_lines`), and oversized input (`test_parse_numstat_input_too_large`).
- Unified-diff parsing: acceptance input (`test_parse_unified_diff_acceptance`), deletion (`test_parse_unified_diff_deletion`), binary files (`test_parse_unified_diff_binary`), headers and binary literals (`test_parse_unified_diff_headers_and_binary_literals`), empty input (`test_parse_unified_diff_empty`), multiple files (`test_parse_unified_diff_multiple_files`), hunk content that resembles headers (`test_parse_unified_diff_header_like_content_lines`), and oversized input (`test_parse_unified_diff_input_too_large`).
- The basic assessment acceptance case (`test_assess_acceptance_basic`).
