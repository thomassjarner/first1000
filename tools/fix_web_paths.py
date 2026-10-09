"""Resolve Flet's Pyodide module URL against the site's HTML base path."""
from __future__ import annotations

import argparse
import re
from pathlib import Path


_STRING = r'''(?:"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*')'''
_DIRECT_URL = re.compile(rf"\bflet\.pyodideUrl\s*=\s*(?P<url>{_STRING})\s*;")
_RESOLVED_URL = re.compile(
    rf"\bflet\.pyodideUrl\s*=\s*new URL\(\s*{_STRING}\s*,\s*document\.baseURI\s*\)\.href\s*;"
)


def has_resolved_pyodide_url(html: str) -> bool:
    return len(_RESOLVED_URL.findall(html)) == 1 and not _DIRECT_URL.search(html)


def resolve_pyodide_url(html: str) -> str:
    """Keep the generated URL, but make it valid for a module worker's import()."""
    if has_resolved_pyodide_url(html):
        return html
    assignments = list(_DIRECT_URL.finditer(html))
    if len(assignments) != 1 or _RESOLVED_URL.search(html):
        raise ValueError("Expected exactly one generated flet.pyodideUrl assignment")
    assignment = assignments[0]
    resolved = f"flet.pyodideUrl = new URL({assignment['url']}, document.baseURI).href;"
    return html[:assignment.start()] + resolved + html[assignment.end():]


def fix_distribution(dist: Path) -> None:
    index = dist / "index.html"
    original = index.read_text(encoding="utf-8")
    fixed = resolve_pyodide_url(original)
    if fixed != original:
        index.write_text(fixed, encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dist", type=Path)
    fix_distribution(parser.parse_args().dist)
    print("Pyodide module URL resolved against document.baseURI.")
