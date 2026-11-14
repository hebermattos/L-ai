"""Safe, bounded, offline PDF/EPUB text extraction for RAG."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from zipfile import BadZipFile, ZipFile

MAX_PDF_BYTES = 30 * 1024 * 1024
MAX_EPUB_BYTES = 20 * 1024 * 1024
MAX_EPUB_UNPACKED = 80 * 1024 * 1024
MAX_TEXT_CHARS = 2_000_000
MAX_PAGES = 500


class DocumentError(ValueError):
    pass


@dataclass(frozen=True)
class ExtractedDocument:
    source: str
    title: str
    body: str
    author: str = ""


def file_paths(files: list[Path], directory: Path | None, limit: int = 50) -> list[Path]:
    if not 1 <= limit <= 100:
        raise DocumentError("Document limit must be 1..100")
    candidates = list(files)
    if directory:
        if not directory.is_dir() or directory.is_symlink():
            raise DocumentError("Document directory must be a real directory")
        candidates.extend(p for p in directory.rglob("*") if p.suffix.lower() in (".pdf", ".epub"))
    output = []
    seen = set()
    for path in candidates:
        if path.is_symlink() or not path.is_file() or path.suffix.lower() not in (".pdf", ".epub"):
            raise DocumentError(f"Not a regular PDF/EPUB: {path}")
        real = path.resolve()
        if real not in seen:
            seen.add(real)
            output.append(real)
        if len(output) > limit:
            raise DocumentError("Too many documents")
    return output


def _check_epub_archive(path: Path):
    try:
        with ZipFile(path) as archive:
            entries = archive.infolist()
            if len(entries) > 500:
                raise DocumentError("EPUB has too many archive entries")
            total = 0
            for entry in entries:
                total += entry.file_size
                if total > MAX_EPUB_UNPACKED:
                    raise DocumentError("EPUB exceeds uncompressed size limit")
                if entry.file_size > 0 and entry.file_size / max(1, entry.compress_size) > 100:
                    raise DocumentError("EPUB compression ratio exceeds limit")
                if entry.flag_bits & 1:
                    raise DocumentError("Encrypted EPUB entries are not supported")
                # Reject symlinks embedded in ZIPs.
                if (entry.external_attr >> 16) & 0o170000 == 0o120000:
                    raise DocumentError("EPUB contains a symbolic link")
    except (BadZipFile, OSError) as exc:
        raise DocumentError("EPUB is not a valid ZIP container") from exc


def read_document(path: Path) -> ExtractedDocument:
    path = path.resolve()
    size = path.stat().st_size
    if path.suffix.lower() == ".pdf":
        if size > MAX_PDF_BYTES:
            raise DocumentError("PDF exceeds 30 MiB")
        import fitz
        with fitz.open(path) as doc:
            if doc.needs_pass:
                raise DocumentError("Password-protected PDF is unsupported")
            if doc.page_count > MAX_PAGES:
                raise DocumentError("PDF has too many pages")
            meta = doc.metadata or {}
            title = (meta.get("title") or path.stem).strip()
            author = (meta.get("author") or "").strip()
            blocks = []
            total = 0
            for i, page in enumerate(doc):
                text = page.get_text("text").strip()
                if not text:
                    continue
                total += len(text)
                if total > MAX_TEXT_CHARS:
                    raise DocumentError("PDF extracted text is too large")
                blocks.append(f"## Página {i+1}\n\n{text}")
            body = "\n\n".join(blocks)
    elif path.suffix.lower() == ".epub":
        if size > MAX_EPUB_BYTES:
            raise DocumentError("EPUB exceeds 20 MiB")
        _check_epub_archive(path)
        from ebooklib import epub, ITEM_DOCUMENT
        from bs4 import BeautifulSoup
        book = epub.read_epub(str(path), options={"ignore_ncx": True})
        title_data = book.get_metadata("DC", "title")
        author_data = book.get_metadata("DC", "creator")
        title = str(title_data[0][0]) if title_data else path.stem
        author = str(author_data[0][0]) if author_data else ""
        blocks = []
        total = 0
        for item in book.get_items():
            if item.get_type() != ITEM_DOCUMENT:
                continue
            soup = BeautifulSoup(item.get_content(), "html.parser")
            for tag in soup(["script", "style", "nav"]):
                tag.decompose()
            text = soup.get_text("\n", strip=True)
            if not text:
                continue
            total += len(text)
            if total > MAX_TEXT_CHARS:
                raise DocumentError("EPUB extracted text is too large")
            blocks.append(text)
        body = "\n\n".join(blocks)
    else:
        raise DocumentError("Unsupported document format")
    if len(body.strip()) < 100:
        raise DocumentError("No substantial text; scanned PDFs require OCR (future P1)")
    return ExtractedDocument(source=path.as_uri(), title=title, author=author, body=body)


def format_document(doc: ExtractedDocument) -> str:
    # Do not embed private absolute filesystem paths in retrieved passages.
    return (f"# {doc.title}\n\nAutor: {doc.author or 'não informado'}\n"
            f"Formato: {Path(doc.source).suffix.lower().lstrip('.')}\n\n{doc.body}\n")
