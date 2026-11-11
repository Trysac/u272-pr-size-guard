# trysac-pr-size-guard

Measure pull request size from git numstat or unified diffs. The library counts added plus deleted lines for non-binary files, applies a documented ignore list, returns `ok`/`warn`/`fail` against thresholds, and suggests directory-based slices that fit under a line limit.

## Installation

Python 3.10 or newer is required. The package uses only the Python standard library and has no runtime dependencies. The import name is `pr_size_guard`; the module can be run as `python -m pr_size_guard`. In this repository, put `src/` on `PYTHONPATH` (for example `PYTHONPATH=src python -m pytest`) so the package is importable.

## Usage

```python
from pr_size_guard import parse_numstat, assess, suggest_slices

numstat = "10\t2\tsrc/app.py\n-\t-\tlogo.png\n"
changes = parse_numstat(numstat)
result = assess(changes)
print(result.status)  # ok
print(result.counted)  # 12
slices = suggest_slices(changes, limit=400, depth=1)
print(slices[0].groups)  # ('src',)
```

CLI:

```sh
python -m pr_size_guard --numstat stat.txt --suggest
```

`FILE` may be `-` to read stdin.

## API

- `FileChange(path: str, added: int, deleted: int, binary: bool = False)`: frozen dataclass. `FileChange.lines` is `added + deleted`.
- `Assessment(status: Literal['ok', 'warn', 'fail'], counted: int, ignored: int, files: int)`: frozen dataclass returned by `assess`.
- `Slice(groups: tuple[str, ...], lines: int, oversized: bool)`: frozen dataclass returned by `suggest_slices`.
- `parse_numstat(text: str) -> list[FileChange]`: parses `git diff --numstat` lines of the form `<added>\t<deleted>\t<path>`. `-\t-\t<path>` is binary with 0 added and 0 deleted. Renames such as `old => new` and `pre/{old => new}/post` resolve to the new path; duplicate slashes are collapsed.
- `parse_unified_diff(text: str) -> list[FileChange]`: counts `+` and `-` hunk lines, excludes `+++`/`---` headers and `\ No newline at end of file`, takes the path from `+++ b/<path>` or `--- a/<path>` for deletions, and marks `Binary files a/x and b/x differ` as binary.
- `assess(changes, *, warn: int = 400, fail: int = 1000, ignore: Sequence[str] = DEFAULT_IGNORE) -> Assessment`: binary files count 0 and are not counted as files. Ignored files add to `ignored`; non-ignored files add to `counted` and `files`. Status is `ok` when `counted <= warn`, `warn` when `counted <= fail`, otherwise `fail`.
- `suggest_slices(changes, *, limit: int = 400, depth: int = 1, ignore: Sequence[str] = DEFAULT_IGNORE) -> list[Slice]`: groups by the first `depth` directory segments (`.` for root files), sorts groups by lines descending then name, packs first-fit decreasing under `limit`, and emits a group larger than `limit` as its own `oversized` slice. Output slices sort by oversized first, then lines descending, then first group name.
- `DEFAULT_IGNORE`: `package-lock.json`, `pnpm-lock.yaml`, `yarn.lock`, `poetry.lock`, `uv.lock`, `Cargo.lock`, `go.sum`, `*.min.js`, `*.snap`, `vendor/**`, `dist/**`, `node_modules/**`, `__snapshots__/**`.
- `PrSizeError(code, message: str = "")`: `code` is one of `parse_error`, `input_too_large`, `invalid_pattern`, `invalid_options`.

Ignore patterns have two allowed forms. A pattern without `/` is matched with `fnmatch.fnmatchcase` against the basename; `dirname/**` matches when `dirname` is any directory segment of the path. Any other pattern raises `PrSizeError` with code `invalid_pattern`. The CLI `--ignore PATTERN` is repeatable and replaces the default list.

Limits and validation: both parsers reject input longer than `MAX_INPUT_LENGTH = 52_428_800` characters with code `input_too_large`. A malformed numstat line (not three tab-separated fields, non-integer counts, or negative counts) raises `parse_error` with the line number. `assess` raises `invalid_options` for negative thresholds or `warn >= fail`. `suggest_slices` raises `invalid_options` for `limit <= 0` or `depth <= 0`.

CLI options: `--numstat FILE` or `--diff FILE` (exactly one required), `--warn` (default 400), `--fail` (default 1000), `--limit` (default 400), `--depth` (default 1), `--suggest`, and repeatable `--ignore PATTERN`. It prints one status line such as `status: warn (512 lines counted, 2000 ignored)`; `--suggest` adds one line per slice. Exit codes are 0 for `ok` or `warn`, 1 for `fail`, and 2 for usage or input errors.

## Why not CI size labels

CI size labels usually count every changed line and report only that a pull request is too big. This utility counts added plus deleted lines only for non-ignored, non-binary files, exposes the warn/fail thresholds, and returns concrete directory-based slices. It does not call git or the GitHub API, comment on pull requests, or post labels.

## Security

See [docs/SECURITY.md](docs/SECURITY.md).
