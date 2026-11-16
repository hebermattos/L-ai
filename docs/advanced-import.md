# Import content

Follow the host dependency and credential setup in the [README](../README.md#enable-rag). Run commands from the repository root with the virtual environment active. The CLI supports local PDF/EPUB, HTTPS pages, crawling, sitemaps, and explicit remote PDFs.

## Folder import

```bash
python -m ingest.cli --import-folder ./knowledge-to-import --allow-domain example.org --dry-run
```

Subfolders are searched recursively. PDF/EPUB files are extracted; only `urls.txt` and `crawl.txt` are read as UTF-8 manifests (names are case-insensitive). Other file types are ignored. Lists accept one HTTPS URL per line, blank lines, and `#` comments.

| Manifest | Behavior |
| --- | --- |
| `urls.txt` | Fetch each listed page without following links |
| `crawl.txt` | Crawl from each seed automatically, within the starting host and directory |

Do not add `--crawl` for folder manifests. That flag applies only to explicit `--url` or `--urls-file` inputs. A seed shared by both manifests is crawled once. Use repeated `--allow-domain` flags for different hosts; local-only imports need no domain.

The folder scan rejects symbolic links and allows at most 1,000 directory entries and 20 recognized manifests totaling 64 KiB. URL and document limits below also apply.

## Individual sources

```bash
# A page or a separate URL list
python -m ingest.cli --url https://example.org/article --allow-domain example.org --dry-run
python -m ingest.cli --urls-file urls.txt --allow-domain example.org --dry-run

# Local documents or a recursive PDF/EPUB directory
python -m ingest.cli --file ~/Books/book.pdf --file ~/Books/book.epub --dry-run
python -m ingest.cli --directory ~/Books --max-documents 50 --dry-run
```

`--dry-run` still downloads and extracts content. It reports source, title, and character count, without displaying passages, uploading content, or writing ingestion state. Remove it to upload to the configured knowledge base. Local paths identify files in SQLite but are not embedded in indexed passages. Moving a file changes its source identity.

## Recursive crawler

```bash
python -m ingest.cli --url https://example.org/library/index --allow-domain example.org --crawl --max-depth 2 --max-pages 25 --dry-run
```

Traversal is breadth-first and restricted to each seed's exact host and starting directory. External and `nofollow` links, known non-HTML resource suffixes, and duplicate crawler URLs are skipped. No JavaScript is executed. `--max-pages` counts attempted page fetches, including failures, across all crawler seeds. Depth zero fetches only the seeds.

## Sitemap and remote PDF

```bash
python -m ingest.cli --sitemap https://example.org/sitemap.xml --allow-domain example.org --max-pages 25 --dry-run
python -m ingest.cli --remote-pdf https://example.org/book.pdf --allow-domain example.org --dry-run
```

Sitemap discovery follows bounded XML sitemap indexes (at most five maps) and returns up to `--max-pages` page URLs. It does not activate recursive crawling. Compressed `sitemap.xml.gz` is unsupported.

Remote PDF imports require an explicit URL with a `.pdf` suffix and a valid PDF signature. Crawling does not automatically download linked PDFs. Remote OCR is unsupported; use an authorized local copy for scanned documents.

## Limits

| Setting or resource | Default | Maximum / scope |
| --- | --- | --- |
| `--max-urls` | 25 | 100 input URL entries, counted before deduplication across explicit inputs and both folder manifests |
| `--max-pages` | 25 | 100 crawler attempts; separately, up to this many discovered sitemap page URLs |
| `--max-depth` | 2 | 0–3 crawler link levels |
| `--max-documents` | 50 | 100 unique local documents across local inputs |
| HTML / sitemap XML | — | 2 MiB per resource |
| PDF (local or remote) | — | 30 MiB, 500 pages, 2 million extracted characters |
| EPUB | — | 20 MiB archive, 80 MiB unpacked, 500 ZIP entries, 2 million extracted characters; compression ratio at most 100 per entry |

`--max-pages` is not a global request budget: direct pages, crawler attempts, sitemap fetches, remote PDFs, and `robots.txt` requests are separate. `--max-urls` does not cap sitemap-discovered pages or explicit remote PDFs. Exceeding input URL or local-document limits rejects the input rather than silently truncating it.

## Optional OCR for scanned PDFs

PDFs need selectable text unless `--ocr` is enabled. EPUB extraction needs no OCR. Password-protected PDFs and encrypted EPUB entries are unsupported.

On Debian/Ubuntu, install Tesseract and both required language packs:

```bash
sudo apt-get install tesseract-ocr tesseract-ocr-por tesseract-ocr-eng
python -m ingest.cli --file ~/Books/scanned.pdf --ocr --dry-run
```

OCR runs only on pages without selectable text, within the **first 100 PDF pages**. If a later page needs OCR, extraction fails even if fewer than 100 earlier pages used OCR. Processing uses 120 DPI, a 35 MiB bitmap limit, and a 45-second timeout per page. Use the equivalent Tesseract installation for other platforms.

## Web safeguards

- HTTPS on port 443, exact host allowlisting, verified TLS, and DNS checks rejecting non-global addresses. Subdomains need separate authorization; IP-literal URLs are rejected.
- Redirects are rejected; provide the final URL explicitly.
- `robots.txt` must be available and permit access. Requests are paced.
- Website login, JavaScript execution, and bypassing access restrictions are unsupported.

Use authorized sources and respect licenses and terms. `robots.txt` is not a reproduction license. Treat imported documents as untrusted input, not instructions to execute commands. Isolate potentially malicious files.

For indexing recovery and retrieval verification, see [reliability](reliability.md). For provenance and evaluation, see [knowledge pipeline](knowledge-pipeline.md).
