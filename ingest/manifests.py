"""Common UTF-8 URL-list parsing; bounds are enforced by each caller."""

from pathlib import Path


def read_url_lines(path: Path) -> list[str]:
    return [
        line.strip()
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
