"""Measure pull request size from git diffs.

Counts reviewable lines, ignores lock and generated files, flags warn/fail
thresholds, and suggests how to split the change into reviewable slices.
"""

from __future__ import annotations

import fnmatch
import logging
import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import Literal

__all__ = [
    "DEFAULT_IGNORE",
    "Assessment",
    "FileChange",
    "PrSizeError",
    "Slice",
    "assess",
    "parse_numstat",
    "parse_unified_diff",
    "suggest_slices",
]

logger = logging.getLogger(__name__)
if not logger.handlers:
    logger.addHandler(logging.NullHandler())

MAX_INPUT_LENGTH = 52_428_800  # 50 MiB

DEFAULT_IGNORE: tuple[str, ...] = (
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    "poetry.lock",
    "uv.lock",
    "Cargo.lock",
    "go.sum",
    "*.min.js",
    "*.snap",
    "vendor/**",
    "dist/**",
    "node_modules/**",
    "__snapshots__/**",
)


@dataclass(frozen=True)
class FileChange:
    """A single file change from a diff."""

    path: str
    added: int
    deleted: int
    binary: bool = False

    @property
    def lines(self) -> int:
        """Total changed lines (added + deleted)."""
        return self.added + self.deleted


class PrSizeError(Exception):
    """Base error for pr_size_guard."""

    def __init__(
        self,
        code: Literal[
            "parse_error",
            "input_too_large",
            "invalid_pattern",
            "invalid_options",
        ],
        message: str = "",
    ) -> None:
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}" if message else code)


@dataclass(frozen=True)
class Assessment:
    """Result of size assessment."""

    status: Literal["ok", "warn", "fail"]
    counted: int
    ignored: int
    files: int


@dataclass(frozen=True)
class Slice:
    """A suggested group of directories that fit under the limit."""

    groups: tuple[str, ...]
    lines: int
    oversized: bool


def _validate_pattern(pattern: str) -> None:
    """Raise PrSizeError if pattern is not of the two allowed forms."""
    if "/" not in pattern:
        return
    if not pattern.endswith("/**"):
        raise PrSizeError(
            "invalid_pattern",
            f"Invalid ignore pattern: {pattern!r} (must be 'dirname/**' when it contains '/')",
        )
    dir_part = pattern[:-3]
    if "/" in dir_part:
        raise PrSizeError(
            "invalid_pattern",
            f"Invalid ignore pattern: {pattern!r} (directory must be a single segment)",
        )


def _matches_ignore(path: str, pattern: str) -> bool:
    """Return True if ``path`` matches a validated ignore pattern."""
    basename = path.rsplit("/", 1)[-1]
    if "/" not in pattern:
        return fnmatch.fnmatchcase(basename, pattern)
    # pattern is 'dir/**'
    dir_part = pattern[:-3]
    return dir_part in path.split("/")


def _resolve_rename(path: str) -> str:
    """Resolve git rename path like 'src/{old => new}/util.py' to new path."""

    # Replace all '{old => new}' occurrences with 'new'.
    def replace_brace(match: re.Match[str]) -> str:
        content = match.group(0)[1:-1]  # strip braces
        _, new = content.split(" => ", 1)
        return new

    result = re.sub(r"\{[^{}]* => [^{}]*\}", replace_brace, path)
    if "{" not in result and "}" not in result and " => " in result:
        result = result.split(" => ", 1)[1]
    # Collapse duplicate slashes that may result from the substitution.
    while "//" in result:
        result = result.replace("//", "/")
    return result


def _check_input_length(text: str) -> None:
    """Raise PrSizeError if text exceeds the global input size limit."""
    if len(text) > MAX_INPUT_LENGTH:
        raise PrSizeError(
            "input_too_large",
            f"Input exceeds {MAX_INPUT_LENGTH} characters",
        )


def parse_numstat(text: str) -> list[FileChange]:
    """Parse ``git diff --numstat`` output into FileChange objects.

    Each line is ``<added>\\t<deleted>\\t<path>``. Binary files use ``-\\t-\\t<path>``.
    Rename paths are resolved to the new name (duplicate slashes collapsed).

    Raises:
        PrSizeError: code ``input_too_large`` if input is too long,
            code ``parse_error`` if a line is malformed.
    """
    _check_input_length(text)
    result: list[FileChange] = []
    for line_no, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        parts = line.split("\t")
        if len(parts) != 3:
            raise PrSizeError(
                "parse_error",
                f"Invalid numstat line {line_no}: expected 3 tab-separated fields",
            )
        added_str, deleted_str, path = parts
        if added_str == "-" and deleted_str == "-":
            result.append(FileChange(path=_resolve_rename(path), added=0, deleted=0, binary=True))
            continue
        try:
            added = int(added_str)
            deleted = int(deleted_str)
        except ValueError:
            raise PrSizeError(
                "parse_error",
                f"Invalid numstat line {line_no}: non-integer counts",
            ) from None
        if added < 0 or deleted < 0:
            raise PrSizeError(
                "parse_error",
                f"Invalid numstat line {line_no}: negative counts",
            )
        result.append(
            FileChange(
                path=_resolve_rename(path),
                added=added,
                deleted=deleted,
                binary=False,
            )
        )
    return result


def parse_unified_diff(text: str) -> list[FileChange]:
    """Parse a unified diff into FileChange objects.

    Counts ``+`` and ``-`` lines (excluding ``+++``/``---`` headers), takes the
    path from ``+++ b/<path>`` (or ``--- a/<path>`` for deletions), and marks
    binary files from ``Binary files a/x and b/x differ`` lines.

    Raises:
        PrSizeError: code ``input_too_large`` if input is too long.
    """
    _check_input_length(text)
    result: list[FileChange] = []
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.startswith("diff --git "):
            i += 1
            continue
        path: str | None = None
        added = 0
        deleted = 0
        binary = False
        in_hunk = False
        j = i + 1
        while j < len(lines) and not lines[j].startswith("diff --git "):
            cur = lines[j]
            if cur.startswith("@@ "):
                in_hunk = True
            elif in_hunk:
                # Inside a hunk every '+'/'-' line is content, even when its
                # text makes it look like a '+++'/'---' file header.
                if cur.startswith("+"):
                    added += 1
                elif cur.startswith("-"):
                    deleted += 1
            elif cur.startswith("+++ b/"):
                path = cur[6:]
            elif cur.startswith("--- a/"):
                if path is None or path == "/dev/null":
                    path = cur[6:]
            elif cur.startswith("Binary files "):
                binary = True
                if path is None:
                    match = re.search(r"Binary files a/(.*?) and b/", cur)
                    if match:
                        path = match.group(1)
            j += 1
        if path is not None or binary:
            if path is None:
                path = ""
            result.append(
                FileChange(
                    path=path,
                    added=0 if binary else added,
                    deleted=0 if binary else deleted,
                    binary=binary,
                )
            )
        i = j
    return result


def assess(
    changes: Iterable[FileChange],
    *,
    warn: int = 400,
    fail: int = 1000,
    ignore: Sequence[str] = DEFAULT_IGNORE,
) -> Assessment:
    """Assess the size of changes against warn/fail thresholds.

    Binary files contribute 0 counted lines and are excluded from file count.
    Ignored files contribute to ``ignored`` instead of ``counted``.

    Raises:
        PrSizeError: code ``invalid_options`` if thresholds are invalid,
            code ``invalid_pattern`` if an ignore pattern is invalid.
    """
    if warn < 0 or fail < 0:
        raise PrSizeError("invalid_options", "warn and fail must be non-negative")
    if warn >= fail:
        raise PrSizeError("invalid_options", "warn must be less than fail")
    for pattern in ignore:
        _validate_pattern(pattern)

    counted = 0
    ignored = 0
    files = 0
    for change in changes:
        if change.binary:
            continue
        lines = change.lines
        if any(_matches_ignore(change.path, p) for p in ignore):
            ignored += lines
        else:
            counted += lines
            files += 1

    status: Literal["ok", "warn", "fail"]
    if counted <= warn:
        status = "ok"
    elif counted <= fail:
        status = "warn"
    else:
        status = "fail"
    return Assessment(status=status, counted=counted, ignored=ignored, files=files)


def _group_key(path: str, depth: int) -> str:
    """Return the group key for a path: first ``depth`` directory segments."""
    parts = path.split("/")
    if len(parts) == 1:
        return "."
    dirs = parts[:-1]
    selected = dirs[:depth] if depth < len(dirs) else dirs
    if not selected:
        return "."
    return "/".join(selected)


def suggest_slices(
    changes: Iterable[FileChange],
    *,
    limit: int = 400,
    depth: int = 1,
    ignore: Sequence[str] = DEFAULT_IGNORE,
) -> list[Slice]:
    """Suggest slices of directory groups that fit under ``limit`` lines.

    Groups are aggregated by the first ``depth`` directory segments, sorted by
    lines descending then name, and packed first-fit decreasing. Oversized
    groups become their own slice.

    Raises:
        PrSizeError: code ``invalid_options`` if limit/depth are invalid,
            code ``invalid_pattern`` if an ignore pattern is invalid.
    """
    if limit <= 0:
        raise PrSizeError("invalid_options", "limit must be positive")
    if depth <= 0:
        raise PrSizeError("invalid_options", "depth must be positive")
    for pattern in ignore:
        _validate_pattern(pattern)

    groups: dict[str, int] = {}
    for change in changes:
        if any(_matches_ignore(change.path, p) for p in ignore):
            continue
        lines = change.lines
        key = _group_key(change.path, depth)
        groups[key] = groups.get(key, 0) + lines

    if not groups:
        return []

    sorted_groups = sorted(groups.items(), key=lambda kv: (-kv[1], kv[0]))
    slices: list[list[tuple[str, int]]] = []
    for key, lines in sorted_groups:
        if lines > limit:
            slices.append([(key, lines)])
            continue
        placed = False
        for sl in slices:
            current_total = sum(group_lines for _, group_lines in sl)
            if current_total + lines <= limit:
                sl.append((key, lines))
                placed = True
                break
        if not placed:
            slices.append([(key, lines)])

    result: list[Slice] = []
    for sl in slices:
        total = sum(group_lines for _, group_lines in sl)
        oversized = len(sl) == 1 and sl[0][1] > limit
        result.append(
            Slice(
                groups=tuple(k for k, _ in sl),
                lines=total,
                oversized=oversized,
            )
        )
    result.sort(key=lambda s: (not s.oversized, -s.lines, s.groups[0] if s.groups else ""))
    return result
