# Crawling and document import

L-ai can recursively follow internal HTML links on authorized websites and import **local PDFs/EPUBs** as well as **explicitly supplied remote PDFs**. Before using the CLI, follow the dependency and credential setup in the [README](../README.md#enable-rag).

## Single-command folder import

Use `--import-folder` to recursively discover PDF/EPUB files and URL lists in a single directory:

```bash
python -m ingest.cli --import-folder ./knowledge-to-import --allow-domain example.org --dry-run
```

Each `.txt` file in the folder tree is interpreted as a UTF-8 URL list (one HTTPS URL per line with optional blank lines and `#` comments). PDF/EPUB files are extracted locally. URLs must be explicitly authorized with `--allow-domain`; existing network restrictions and `robots.txt` checks remain in force. The command uses the normal Open WebUI credentials when `--dry-run` is removed. Optional `--crawl`, `--max-depth`, `--max-pages`, `--max-documents`, and `--ocr` flags remain available. Symbolic links are rejected. At most 20 URL lists (64 KiB combined) and 1,000 directory entries are examined per run; other file types are ignored. Default URL and document limits still apply.

Example folder layout:

```text
knowledge-to-import/
├── books/
│   ├── manual.pdf
│   └── reference.epub
├── resources.txt
└── more-urls.txt
```

## Recursive crawler

```bash
python -m ingest.cli --url https://example.org/library/index --allow-domain example.org --crawl --max-depth 2 --max-pages 25 --dry-run
```

The crawler performs breadth-first traversal within the original URL's domain and directory. It skips external links, `nofollow` links, non-HTML resources, and duplicate URLs. It does not execute JavaScript. Depth (0–3) and page-attempt (1–100) limits apply per run. For sitemap discovery, see [web ingestion](web-ingestion.md).

## Local PDF and EPUB

```bash
python -m ingest.cli --file ~/Books/book.pdf --file ~/Books/book.epub --dry-run
python -m ingest.cli --directory ~/Books --max-documents 50 --dry-run
```

Directories are traversed recursively; symbolic links are rejected. PDFs must contain selectable text unless optional OCR is enabled. EPUB extraction does not require OCR; encrypted EPUBs are unsupported. Titles and authors are retained when available, and PDF passages include page markers.

Limits: PDFs up to 30 MiB, 500 pages, and 2 million extracted characters; EPUBs up to 20 MiB, 80 MiB uncompressed, and 500 ZIP entries. Each run processes at most 100 documents (`--max-documents`; default 50).

## Optional OCR for scanned PDFs

Install Tesseract and the Portuguese and English language packs on the host:

```bash
sudo apt-get install tesseract-ocr tesseract-ocr-por tesseract-ocr-eng
python -m ingest.cli --file ~/Books/scanned.pdf --ocr --dry-run
```

OCR runs **only on pages without selectable text**, at 120 DPI, with a 45-second timeout per page and a 100-page OCR limit. Start with `--dry-run`. CPU-based processing may be slow.

## Remote PDF

```bash
python -m ingest.cli --remote-pdf https://example.org/book.pdf --allow-domain example.org --dry-run
```

Requires HTTPS, `robots.txt` permission, an allowlisted domain, a `.pdf` suffix, and a valid PDF signature. Remote OCR is not supported; obtain an authorized local copy for scanned documents. See [web ingestion](web-ingestion.md) for collection safeguards.

## Indexing

Remove `--dry-run` to upload passages to Open WebUI after configuring API credentials and a knowledge base. Local state uses content hashes to avoid reindexing identical documents. Local files are identified by URIs in the state database, but absolute paths are not embedded in indexed passages. Verify retrieval using known sources in chat; see [reliability](reliability.md).
