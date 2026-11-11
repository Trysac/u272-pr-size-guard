# Security notes

## Threat model

### Defended

- The library functions (`parse_numstat`, `parse_unified_diff`, `assess`, `suggest_slices`) do not open files, spawn processes, use the network, call git, or call the GitHub API. They operate on strings and `FileChange` objects.
- The CLI (`python -m pr_size_guard`) reads exactly one of `--numstat FILE` or `--diff FILE`, or stdin when FILE is `-`, using UTF-8 for files. It does not invoke a shell or evaluate input.
- Input over `MAX_INPUT_LENGTH = 52_428_800` characters is rejected by both parsers with `PrSizeError` code `input_too_large` before line parsing.
- Malformed numstat lines (not three tab-separated fields, non-integer counts, negative counts) raise `PrSizeError` code `parse_error` including the line number.
- Ignore patterns are validated: a pattern either has no `/` and is matched against the basename with `fnmatch.fnmatchcase`, or is `dirname/**` and is matched against directory segments. Other patterns raise `PrSizeError` code `invalid_pattern`; user input is never compiled as a regular expression.
- Invalid options (`warn`/`fail` negative or `warn >= fail`, `limit <= 0`, `depth <= 0`) raise `PrSizeError` code `invalid_options`.
- No `eval`, `exec`, `pickle`, `yaml`, or other deserialization is used. The only regex used with a fixed pattern is rename cleanup in `_resolve_rename`.

### Not defended

- Resource exhaustion below the 52,428,800-character cap: very large diffs can still consume memory and CPU proportional to input size.
- Filesystem access by the CLI: `FILE` is opened with the permissions of the invoking user; path traversal is not restricted beyond normal OS permissions.
- Terminal output is derived from diff paths. The code does not strip control characters from paths before printing slice groups or status.
- Secrets, credentials, authentication, network transport, and publishing are not handled by the code.

## Publishing

No publishing configuration, credentials, or release automation is present in this code snapshot. This code does not define a vulnerability reporting process.
