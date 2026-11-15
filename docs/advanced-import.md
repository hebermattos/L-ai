# Crawling and document imports

L-ai can follow internal HTML links on authorized sites and import **local PDF/EPUB files**, as well as **explicitly specified remote PDFs**. Set up dependencies and credentials using the [README](../README.md#enable-rag).

## Recursive crawler

```bash
python -m ingest.cli --url https://example.org/library/index --allow-domain example.org --crawl --max-depth 2 --max-pages 25 --dry-run
```

The crawler uses breadth-first traversal within the seed URL's host and directory. It skips external links, `nofollow`, non-HTML resources and duplicate URLs; it does not execute JavaScript. Depth is limited to 0–3 and page attempts to 1–100 per run. See [web ingestion](web-ingestion.md) for sitemap discovery.

## Local PDF and EPUB

```bash
python -m ingest.cli --file ~/Books/book.pdf --file ~/Books/book.epub --dry-run
python -m ingest.cli --directory ~/Books --max-documents 50 --dry-run
```

Directory traversal is recursive; symbolic links are rejected. PDFs must include selectable text or use optional OCR. EPUB OCR is not needed; encrypted content is unsupported. Title and author metadata are preserved where available, and PDFs include page markers.

Limits: PDF up to 30 MiB, 500 pages, and 2 million extracted characters; EPUB up to 20 MiB, 80 MiB decompressed, and 500 ZIP entries. At most 100 documents per run (`--max-documents`, default 50).

## Optional OCR for scanned PDFs

Install Tesseract and Portuguese/English language packs on the host:

```bash
sudo apt-get install tesseract-ocr tesseract-ocr-por tesseract-ocr-eng
python -m ingest.cli --file ~/Books/scanned.pdf --ocr --dry-run
```

OCR runs **only on pages without selectable text**, at 120 DPI, with a 45-second timeout per page and a 100-page OCR limit. Try `--dry-run` first; CPU-only processing can be slow.

## Remote PDFs

```bash
python -m ingest.cli --remote-pdf https://example.org/book.pdf --allow-domain example.org --dry-run
```

Requires HTTPS, `robots.txt` compliance, an authorized domain, the `.pdf` extension and a PDF signature. There is no remote OCR; obtain an authorized local copy for scanned documents. See [web ingestion](web-ingestion.md) for safeguards.

## Indexing

Remove `--dry-run` to upload passages to Open WebUI after setting credentials. Local state uses content hashes to avoid reindexing unchanged documents. Local files are identified by URI in the state database, but absolute paths are not embedded into indexed text. Verify retrieval with known sources in chat; see [reliability](reliability.md).
