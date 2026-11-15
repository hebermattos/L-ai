"""Discover bounded local documents and HTTPS URL lists in one folder."""

from __future__ import annotations

from pathlib import Path

from .documents import DocumentError

MAX_MANIFESTS = 20
MAX_MANIFEST_BYTES = 65536
MAX_DISCOVERED_ENTRIES = 1000


def discover_import_folder(directory: Path) -> tuple[list[Path], list[str]]:
    """Recursively find PDF/EPUB files and .txt URL manifests.

    TXT files are treated as URL lists, not indexed as document text.
    Existing URL validation and allowlisting are applied by the CLI.
    """
    if directory.is_symlink() or not directory.is_dir():
        raise DocumentError("Import folder must be a real directory")

    documents: list[Path] = []
    urls: list[str] = []
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
        elif suffix == ".txt":
            manifest_count += 1
            if manifest_count > MAX_MANIFESTS:
                raise DocumentError("Too many URL list files (maximum 20)")
            size = path.stat().st_size
            bytes_read += size
            if bytes_read > MAX_MANIFEST_BYTES:
                raise DocumentError("URL lists exceed the combined 64 KiB limit")
            try:
                lines = path.read_text(encoding="utf-8").splitlines()
            except UnicodeError as exc:
                raise DocumentError(f"URL list is not UTF-8: {path}") from exc
            urls.extend(line.strip() for line in lines
                        if line.strip() and not line.lstrip().startswith("#"))

    return documents, urls
