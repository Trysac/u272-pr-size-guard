"""Command-line interface for pr_size_guard."""

from __future__ import annotations

import argparse
import sys

from . import (
    DEFAULT_IGNORE,
    PrSizeError,
    assess,
    parse_numstat,
    parse_unified_diff,
    suggest_slices,
)


def _read_input(filename: str) -> str:
    if filename == "-":
        return sys.stdin.read()
    with open(filename, encoding="utf-8") as f:
        return f.read()


def main(argv: list[str] | None = None) -> int:
    """Run the CLI. Returns 0 (ok/warn), 1 (fail), 2 (usage/input error)."""
    parser = argparse.ArgumentParser(
        prog="pr-size-guard",
        description="Measure pull request size from git numstat or unified diff.",
    )
    parser.add_argument(
        "--numstat",
        metavar="FILE",
        help="read git diff --numstat output from FILE ('-' for stdin)",
    )
    parser.add_argument(
        "--diff",
        metavar="FILE",
        help="read unified diff from FILE ('-' for stdin)",
    )
    parser.add_argument("--warn", type=int, default=400, help="warn threshold (default 400)")
    parser.add_argument("--fail", type=int, default=1000, help="fail threshold (default 1000)")
    parser.add_argument("--limit", type=int, default=400, help="slice line limit (default 400)")
    parser.add_argument(
        "--depth", type=int, default=1, help="directory depth for grouping (default 1)"
    )
    parser.add_argument(
        "--suggest",
        action="store_true",
        help="print suggested slices after the status line",
    )
    parser.add_argument(
        "--ignore",
        action="append",
        metavar="PATTERN",
        help="ignore pattern (repeatable; replaces default ignore list)",
    )

    try:
        args = parser.parse_args(argv)
        if (args.numstat is None) == (args.diff is None):
            parser.error("exactly one of --numstat or --diff is required")
    except SystemExit as e:
        return int(e.code or 2)

    if args.numstat is not None:
        filename = args.numstat
        parse_fn = parse_numstat
    else:
        filename = args.diff
        parse_fn = parse_unified_diff

    try:
        content = _read_input(filename)
        changes = parse_fn(content)
        ignore = args.ignore if args.ignore is not None else DEFAULT_IGNORE
        assessment = assess(changes, warn=args.warn, fail=args.fail, ignore=ignore)
        print(
            f"status: {assessment.status} "
            f"({assessment.counted} lines counted, {assessment.ignored} ignored)"
        )
        if args.suggest:
            slices = suggest_slices(
                changes,
                limit=args.limit,
                depth=args.depth,
                ignore=ignore,
            )
            for i, sl in enumerate(slices, 1):
                suffix = ", oversized" if sl.oversized else ""
                print(f"slice {i}: {', '.join(sl.groups)} ({sl.lines} lines{suffix})")
        return 0 if assessment.status in ("ok", "warn") else 1
    except (FileNotFoundError, IsADirectoryError, PermissionError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    except PrSizeError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    except Exception as e:  # pragma: no cover - defensive
        print(f"error: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
