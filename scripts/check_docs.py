"""Check that Markdown links to local files resolve inside the repository."""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
LINK = re.compile(r"!?\[[^\]]*\]\(([^)]+)\)")


def main() -> int:
    """Report Markdown links that point to missing local files."""
    broken: list[str] = []
    for markdown in ROOT.rglob("*.md"):
        if ".git" in markdown.parts or ".venv" in markdown.parts:
            continue
        content = markdown.read_text(encoding="utf-8")
        for match in LINK.finditer(content):
            target = match.group(1).strip().split(maxsplit=1)[0].strip("<>")
            parsed = urlsplit(target)
            if parsed.scheme or target.startswith("//"):
                continue
            path = unquote(parsed.path)
            destination = (markdown.parent / path).resolve() if path else markdown.resolve()
            if not destination.exists():
                broken.append(f"{markdown.relative_to(ROOT)}: {target}")
    if broken:
        print("Broken local Markdown links:")
        print("\n".join(f"- {item}" for item in broken))
        return 1
    print("All local Markdown links resolve.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
