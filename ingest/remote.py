"""Remote PDF handling without writing untrusted content to disk."""
from urllib.parse import urlsplit
from .documents import DocumentError, MAX_PDF_BYTES, MAX_PAGES, ExtractedDocument, extract_pdf_body
from .web import normalized_url, SourceRejected

def read_remote_pdf(fetcher, url):
    safe = normalized_url(url, fetcher.domains)
    if not urlsplit(safe).path.lower().endswith(".pdf"):
        raise SourceRejected("Remote resource must have a .pdf suffix")
    data = fetcher.get_resource(safe, allowed_types=("pdf",), max_bytes=MAX_PDF_BYTES)
    import fitz
    try:
        with fitz.open(stream=data, filetype="pdf") as pdf:
            if pdf.needs_pass or pdf.page_count > MAX_PAGES:
                raise DocumentError("Encrypted or oversized PDF")
            metadata = pdf.metadata or {}
            body = extract_pdf_body(pdf, text_limit_error="Extracted text too large")
            if len(body) < 100:
                raise DocumentError("PDF without selectable text; use OCR on an authorized local copy")
            return ExtractedDocument(
                source=safe, title=(metadata.get("title") or safe.rsplit("/",1)[-1]).strip(),
                author=(metadata.get("author") or "").strip(), body=body)
    except (ValueError, RuntimeError) as exc:
        raise DocumentError("Invalid remote PDF") from exc
