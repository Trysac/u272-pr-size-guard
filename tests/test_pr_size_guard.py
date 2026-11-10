"""Tests for pr_size_guard."""

from __future__ import annotations

import logging
import sys
from pathlib import Path

import pytest

import pr_size_guard
from pr_size_guard import (
    Assessment,
    FileChange,
    PrSizeError,
    Slice,
    assess,
    parse_numstat,
    parse_unified_diff,
    suggest_slices,
)


def test_file_change_lines_and_frozen() -> None:
    fc = FileChange("a.py", 10, 20, False)
    assert fc.lines == 30
    with pytest.raises(AttributeError):
        fc.added = 5  # type: ignore[misc]


def test_pr_size_error_code() -> None:
    err = PrSizeError("parse_error", "bad line")
    assert err.code == "parse_error"
    assert "parse_error" in str(err)
    assert "bad line" in str(err)


def test_logger_has_null_handler() -> None:
    logger = logging.getLogger("pr_size_guard")
    assert any(isinstance(h, logging.NullHandler) for h in logger.handlers)


# ---------------- parse_numstat ----------------


def test_parse_numstat_acceptance() -> None:
    text = "10\t2\tsrc/app.py\n-\t-\tlogo.png\n5\t0\tsrc/{old => new}/util.py\n"
    expected = [
        FileChange("src/app.py", 10, 2, False),
        FileChange("logo.png", 0, 0, True),
        FileChange("src/new/util.py", 5, 0, False),
    ]
    assert parse_numstat(text) == expected


def test_parse_numstat_basic_and_spaces() -> None:
    text = "3\t1\tsrc/my file.py\n"
    result = parse_numstat(text)
    assert result == [FileChange("src/my file.py", 3, 1, False)]


def test_parse_numstat_rename_whole_path() -> None:
    text = "2\t2\told => new\n"
    assert parse_numstat(text) == [FileChange("new", 2, 2, False)]


def test_parse_numstat_duplicate_slash_collapse() -> None:
    text = "1\t0\ta/{b => }/c.py\n"  # creates a//c.py
    result = parse_numstat(text)
    assert result[0].path == "a/c.py"


def test_parse_numstat_invalid_line() -> None:
    with pytest.raises(PrSizeError) as exc:
        parse_numstat("abc\n")
    assert exc.value.code == "parse_error"
    assert "line 1" in str(exc.value)


def test_parse_numstat_invalid_counts() -> None:
    with pytest.raises(PrSizeError) as exc:
        parse_numstat("x\t2\tfile.py\n")
    assert exc.value.code == "parse_error"


def test_parse_numstat_negative_counts() -> None:
    with pytest.raises(PrSizeError) as exc:
        parse_numstat("-1\t2\tfile.py\n")
    assert exc.value.code == "parse_error"


def test_parse_numstat_skips_blank_lines() -> None:
    assert parse_numstat("1\t0\ta.py\n\n") == [FileChange("a.py", 1, 0, False)]


def test_parse_numstat_input_too_large(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(pr_size_guard, "MAX_INPUT_LENGTH", 10)
    with pytest.raises(PrSizeError) as exc:
        parse_numstat("1\t2\tfile.py\n")  # length 13
    assert exc.value.code == "input_too_large"


# ---------------- parse_unified_diff ----------------


def test_parse_unified_diff_acceptance() -> None:
    diff = """diff --git a/src/a.py b/src/a.py
index 111..222 100644
--- a/src/a.py
+++ b/src/a.py
@@ -1,2 +1,3 @@
 context
+added line
-deleted line
\\ No newline at end of file
"""
    result = parse_unified_diff(diff)
    assert result == [FileChange("src/a.py", 1, 1, False)]


def test_parse_unified_diff_deletion() -> None:
    diff = """diff --git a/old.txt b/old.txt
deleted file mode 100644
index 111..000
--- a/old.txt
+++ /dev/null
@@ -1 +0,0 @@
-content
"""
    result = parse_unified_diff(diff)
    assert result == [FileChange("old.txt", 0, 1, False)]


def test_parse_unified_diff_binary() -> None:
    diff = """diff --git a/logo.png b/logo.png
index 111..222 100644
Binary files a/logo.png and b/logo.png differ
"""
    result = parse_unified_diff(diff)
    assert result == [FileChange("logo.png", 0, 0, True)]


def test_parse_unified_diff_headers_and_binary_literals() -> None:
    """Path comes from '+++ b/<path>' or '--- a/<path>', and a line such as
    'Binary files a/x.png and b/x.png differ' marks the file binary.
    """
    diff = (
        "diff --git a/x.png b/x.png\n"
        "index 111..222 100644\n"
        "Binary files a/x.png and b/x.png differ\n"
    )
    result = parse_unified_diff(diff)
    assert result == [FileChange("x.png", 0, 0, True)]


def test_parse_unified_diff_empty() -> None:
    assert parse_unified_diff("") == []


def test_parse_unified_diff_multiple_files() -> None:
    diff = """diff --git a/a.py b/a.py
--- a/a.py
+++ b/a.py
@@ -1 +1,2 @@
+line1
+line2
-remove
---
diff --git a/b.py b/b.py
--- a/b.py
+++ b/b.py
@@ -1 +1 @@
+only
"""
    result = parse_unified_diff(diff)
    # The bare '---' is a removed content line (text '--'), so it counts too.
    assert result == [
        FileChange("a.py", 2, 2, False),
        FileChange("b.py", 1, 0, False),
    ]


def test_parse_unified_diff_header_like_content_lines() -> None:
    """Hunk content that starts with '---'/'+++' is counted, not treated as a
    file header, and does not overwrite the path.
    """
    diff = """diff --git a/q.sql b/q.sql
--- a/q.sql
+++ b/q.sql
@@ -1,2 +1,2 @@
--- old comment
+++ new comment
--- a/fake.py
+++ b/fake.py
"""
    result = parse_unified_diff(diff)
    assert result == [FileChange("q.sql", 2, 2, False)]


def test_parse_unified_diff_input_too_large(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(pr_size_guard, "MAX_INPUT_LENGTH", 20)
    with pytest.raises(PrSizeError) as exc:
        parse_unified_diff("x" * 21)
    assert exc.value.code == "input_too_large"


# ---------------- ignore patterns and assess ----------------


def test_assess_acceptance_basic() -> None:
    changes = [
        FileChange("src/a.py", 300, 0, False),
        FileChange("package-lock.json", 2000, 0, False),
    ]
    result = assess(changes)
    assert result == Assessment(status="ok", counted=300, ignored=2000, files=1)


def test_assess_status_boundaries() -> None:
    changes = [FileChange("a.py", 400, 0, False)]
    assert assess(changes).status == "ok"
    changes = [FileChange("a.py", 401, 0, False)]
    assert assess(changes).status == "warn"
    changes = [FileChange("a.py", 1000, 0, False)]
    assert assess(changes).status == "warn"
    changes = [FileChange("a.py", 1001, 0, False)]
    assert assess(changes).status == "fail"


def test_assess_ignore_patterns() -> None:
    changes = [
        FileChange("web/package-lock.json", 100, 0, False),
        FileChange("pkg/vendor/x/y.go", 200, 0, False),
        FileChange("src/vendors.py", 50, 0, False),
    ]
    result = assess(changes)
    # web/package-lock.json ignored by basename, pkg/vendor/x/y.go ignored by vendor/**
    assert result.counted == 50
    assert result.ignored == 300


def test_assess_invalid_pattern_with_slash() -> None:
    with pytest.raises(PrSizeError) as exc:
        assess([], ignore=["a/b"])
    assert exc.value.code == "invalid_pattern"


def test_assess_invalid_multi_segment_pattern() -> None:
    with pytest.raises(PrSizeError) as exc:
        assess([], ignore=["a/b/**"])
    assert exc.value.code == "invalid_pattern"


def test_assess_invalid_options() -> None:
    with pytest.raises(PrSizeError) as exc:
        assess([], warn=1000, fail=400)
    assert exc.value.code == "invalid_options"


def test_assess_binary_excluded() -> None:
    changes = [
        FileChange("binary.dat", 0, 0, True),
        FileChange("a.py", 10, 0, False),
    ]
    result = assess(changes)
    assert result.counted == 10
    assert result.files == 1


# ---------------- suggest_slices ----------------


def test_suggest_slices_acceptance() -> None:
    changes = [
        FileChange("src/api/x.py", 300, 0, False),
        FileChange("src/db/y.py", 250, 0, False),
        FileChange("docs/z.md", 100, 0, False),
    ]
    result = suggest_slices(changes, limit=400, depth=2)
    expected = [
        Slice(groups=("src/api", "docs"), lines=400, oversized=False),
        Slice(groups=("src/db",), lines=250, oversized=False),
    ]
    assert result == expected


def test_suggest_slices_oversized_first() -> None:
    changes = [
        FileChange("src/big/x.py", 900, 0, False),
        FileChange("a.py", 10, 0, False),
    ]
    result = suggest_slices(changes, limit=400, depth=2)
    assert result[0].oversized is True
    assert result[0].groups == ("src/big",)
    assert result[0].lines == 900


def test_suggest_slices_ignore_and_binary() -> None:
    changes = [
        FileChange("package-lock.json", 1000, 0, False),
        FileChange("logo.png", 0, 0, True),
        FileChange("src/a.py", 300, 0, False),
    ]
    result = suggest_slices(changes, limit=400, depth=1)
    # lock file ignored; binary contributes 0 lines in group '.', which
    # fits into the first slice together with 'src' (300 lines).
    assert result == [Slice(groups=("src", "."), lines=300, oversized=False)]


def test_suggest_slices_empty_returns_empty() -> None:
    assert suggest_slices([]) == []


def test_suggest_slices_invalid_options() -> None:
    with pytest.raises(PrSizeError) as exc:
        suggest_slices([], limit=0)
    assert exc.value.code == "invalid_options"
    with pytest.raises(PrSizeError):
        suggest_slices([], depth=0)


def test_suggest_slices_invalid_pattern() -> None:
    with pytest.raises(PrSizeError) as exc:
        suggest_slices([], ignore=["bad/pattern"])
    assert exc.value.code == "invalid_pattern"


def test_group_key_depth_rules() -> None:
    # root file
    assert pr_size_guard._group_key("a.py", 1) == "."
    # depth larger than available dirs
    assert pr_size_guard._group_key("src/api/x.py", 3) == "src/api"
    # exact depth
    assert pr_size_guard._group_key("src/api/x.py", 2) == "src/api"
    # no dirs
    assert pr_size_guard._group_key("a.py", 2) == "."


# ---------------- CLI ----------------


def _write_file(tmp_path: Path, name: str, content: str) -> str:
    p = tmp_path / name
    p.write_text(content)
    return str(p)


def test_cli_numstat_warn(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    stat = _write_file(
        tmp_path,
        "stat.txt",
        "512\t0\tsrc/app.py\n2000\t0\tpackage-lock.json\n",
    )
    from pr_size_guard.__main__ import main

    rc = main(["--numstat", stat])
    captured = capsys.readouterr()
    assert rc == 0
    assert captured.out == "status: warn (512 lines counted, 2000 ignored)\n"


def test_cli_fail(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    stat = _write_file(tmp_path, "stat.txt", "1001\t0\ta.py\n")
    from pr_size_guard.__main__ import main

    rc = main(["--numstat", stat])
    assert rc == 1
    assert "status: fail" in capsys.readouterr().out


def test_cli_suggest(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    stat = _write_file(
        tmp_path,
        "stat.txt",
        "300\t0\tsrc/api/x.py\n250\t0\tsrc/db/y.py\n100\t0\tdocs/z.md\n",
    )
    from pr_size_guard.__main__ import main

    rc = main(["--numstat", stat, "--suggest", "--limit", "400", "--depth", "2"])
    captured = capsys.readouterr()
    assert rc == 0
    lines = captured.out.splitlines()
    assert lines[0].startswith("status: warn")
    assert "slice 1: src/api, docs (400 lines)" in lines[1]
    assert "slice 2: src/db (250 lines)" in lines[2]


def test_cli_missing_file_returns_2(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    from pr_size_guard.__main__ import main

    rc = main(["--numstat", str(tmp_path / "missing.txt")])
    assert rc == 2
    assert "error:" in capsys.readouterr().err


def test_cli_stdin(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(sys, "stdin", __import__("io").StringIO("10\t0\ta.py\n"))
    from pr_size_guard.__main__ import main

    rc = main(["--numstat", "-"])
    assert rc == 0
    assert "status: ok" in capsys.readouterr().out


def test_cli_bad_usage(capsys: pytest.CaptureFixture[str]) -> None:
    from pr_size_guard.__main__ import main

    rc = main([])
    assert rc == 2
    assert "usage" in capsys.readouterr().err


def test_cli_invalid_pattern(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    stat = _write_file(tmp_path, "stat.txt", "1\t0\ta.py\n")
    from pr_size_guard.__main__ import main

    rc = main(["--numstat", stat, "--ignore", "bad/pattern"])
    assert rc == 2
    assert "invalid_pattern" in capsys.readouterr().err
