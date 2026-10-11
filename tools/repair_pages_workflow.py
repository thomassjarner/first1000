"""Ensure existing Pages workflows repair the Pyodide URL before validation."""
from __future__ import annotations

import argparse
import re
from pathlib import Path


CHECK = re.compile(r"\b(?P<python>python3?)\s+tools/check_distribution\.py\s+dist(?=\s|['\";]|$)")
FIX = re.compile(r"\bpython3?\s+tools/fix_web_paths\.py\s+dist(?=\s|['\";]|$)")


def repair_text(text: str) -> tuple[str, bool]:
    found = False
    lines = []
    for line in text.splitlines(keepends=True):
        check = CHECK.search(line) if not line.lstrip().startswith("#") else None
        if check:
            found = True
            fix = FIX.search(line)
            if not fix or fix.start() > check.start():
                command = f"{check['python']} tools/fix_web_paths.py dist && {check[0]}"
                line = line[:check.start()] + command + line[check.end():]
        lines.append(line)
    return "".join(lines), found


def repair_workflows(root: Path) -> list[Path]:
    if not (root / "tools/fix_web_paths.py").is_file():
        raise ValueError("Missing tools/fix_web_paths.py. Copy the complete First1000-Fixed project here first.")
    folder = root / ".github/workflows"
    candidates = sorted({*folder.glob("*.yml"), *folder.glob("*.yaml")})
    updates = []
    found = False
    for path in candidates:
        original = path.read_text(encoding="utf-8")
        fixed, has_check = repair_text(original)
        found = found or has_check
        if fixed != original:
            updates.append((path, fixed))
    if not found:
        raise ValueError("No packaged-app check found in .github/workflows. Please attach your workflow file.")
    for path, fixed in updates:
        path.write_text(fixed, encoding="utf-8")
    return [path for path, _ in updates]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    try:
        changed = repair_workflows(args.root.resolve())
    except ValueError as error:
        parser.exit(1, f"{error}\n")
    for path in changed:
        print(f"Updated: {path.relative_to(args.root.resolve())}")
    print("Workflow repair complete." if changed else "Workflow URL repair is already enabled.")
