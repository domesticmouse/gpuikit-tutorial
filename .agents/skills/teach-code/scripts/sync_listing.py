#!/usr/bin/env python3
"""Synchronize or verify Complete Listing fenced code blocks in lesson Markdown files."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[4]
LESSONS_DIR = ROOT_DIR / "lessons"
APPS_DIR = ROOT_DIR / "apps"

COMPLETE_LISTING_RE = re.compile(
    r"(^#{2,3}\s+(?:Step\s+\d+:\s+)?Complete\b[^\n]*\bListing\s*\n"
    r"(?:(?!^```|^#{1,3}\s)[^\n]*\n)*?"
    r"```[^\n]*\n)"
    r"(.*?)"
    r"(^```\s*$)",
    re.MULTILINE | re.DOTALL,
)


def default_source_for_lesson(lesson_path: Path) -> Path:
    stem = lesson_path.stem
    candidate = APPS_DIR / stem / "src" / "main.rs"
    if candidate.exists():
        return candidate
    raise FileNotFoundError(f"Could not infer companion source file for {lesson_path}")


def process_pair(lesson_path: Path, source_path: Path, write: bool) -> bool:
    lesson_text = lesson_path.read_text(encoding="utf-8")
    source_text = source_path.read_text(encoding="utf-8").rstrip("\n") + "\n"

    match = COMPLETE_LISTING_RE.search(lesson_text)
    if not match:
        print(
            f"[ERROR] {lesson_path.relative_to(ROOT_DIR)}: no Complete Listing fenced block found",
            file=sys.stderr,
        )
        return False

    current_body = match.group(2)
    if current_body == source_text:
        line_count = len(source_text.splitlines())
        print(
            f"[OK] {lesson_path.name} == {source_path.relative_to(ROOT_DIR)} ({line_count} lines)"
        )
        return True

    if write:
        updated = (
            lesson_text[: match.start(2)]
            + source_text
            + lesson_text[match.end(2) :]
        )
        lesson_path.write_text(updated, encoding="utf-8")
        line_count = len(source_text.splitlines())
        print(
            f"[UPDATED] {lesson_path.name} <- {source_path.relative_to(ROOT_DIR)} ({line_count} lines)"
        )
        return True

    print(
        f"[MISMATCH] {lesson_path.relative_to(ROOT_DIR)} differs from {source_path.relative_to(ROOT_DIR)}",
        file=sys.stderr,
    )
    return False


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Check or update Complete Listing code blocks in lessons/*.md from apps/*/src/main.rs."
    )
    parser.add_argument("--lesson", type=Path, help="Single lesson Markdown file")
    parser.add_argument("--source", type=Path, help="Companion source file for --lesson")
    parser.add_argument(
        "--write",
        action="store_true",
        help="Rewrite mismatched Complete Listing blocks from companion source files",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify Complete Listing blocks match companion source files (default)",
    )
    args = parser.parse_args()

    if args.source and not args.lesson:
        parser.error("--source requires --lesson")

    pairs: list[tuple[Path, Path]] = []
    if args.lesson:
        lesson = args.lesson.resolve()
        source = args.source.resolve() if args.source else default_source_for_lesson(lesson)
        pairs.append((lesson, source))
    else:
        for lesson in sorted(LESSONS_DIR.glob("[0-9][0-9][0-9][0-9]-*.md")):
            pairs.append((lesson, default_source_for_lesson(lesson)))

    if not pairs:
        print("No lesson files found.", file=sys.stderr)
        return 1

    all_ok = True
    for lesson, source in pairs:
        if not process_pair(lesson, source, write=args.write):
            all_ok = False

    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
