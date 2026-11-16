"""Discover bounded local documents and HTTPS URL lists in one folder."""

from __future__ import annotations

from pathlib import Path

from .documents import DocumentError
from .manifests import read_url_lines

MAX_MANIFESTS = 20
MAX_MANIFEST_BYTES = 65536
MAX_DISCOVERED_ENTRIES = 1000


def discover_import_folder(directory: Path) -> tuple[list[Path], list[str], list[str]]:
    """Find PDF/EPUB files, direct URL lists, and recursive crawl seeds.

    Only urls.txt and crawl.txt are interpreted as manifests. All URL safety
    checks (including allowlisting) are performed by the CLI.
    """
    if directory.is_symlink() or not directory.is_dir():
        raise DocumentError("Import folder must be a real directory")

    documents: list[Path] = []
    urls: list[str] = []
    crawl_urls: list[str] = []
    manifest_count = 0
    bytes_read = 0
    entries = 0

    for path in sorted(directory.rglob("*")):
        entries += 1
        if entries > MAX_DISCOVERED_ENTRIES:
            raise DocumentError("Import folder contains too many entries")
        if path.is_symlink():
            raise DocumentError(f"Symbolic links are not allowed in import folders: {path}")
        if path.is_dir():
            continue
        if not path.is_file():
            raise DocumentError(f"Unsupported filesystem entry: {path}")
        suffix = path.suffix.lower()
        if suffix in {".pdf", ".epub"}:
            documents.append(path)
        elif path.name.lower() in {"urls.txt", "crawl.txt"}:
            manifest_count += 1
            if manifest_count > MAX_MANIFESTS:
                raise DocumentError("Too many URL list files (maximum 20)")
            size = path.stat().st_size
            bytes_read += size
            if bytes_read > MAX_MANIFEST_BYTES:
                raise DocumentError("URL lists exceed the combined 64 KiB limit")
            try:
                lines = read_url_lines(path)
            except UnicodeError as exc:
                raise DocumentError(f"URL list is not UTF-8: {path}") from exc
            target = urls if path.name.lower() == "urls.txt" else crawl_urls
            target.extend(lines)

    return documents, urls, crawl_urls
