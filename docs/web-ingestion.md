# Web ingestion for RAG

This guide documents **currently implemented functionality**: individual URLs, `urls.txt` lists, authorized recursive crawling, sitemap discovery, and explicitly supplied remote PDFs. Trafilatura extracts HTML, and content can be uploaded to an Open WebUI Knowledge base.

## Folder-based URL lists

To ingest local PDF/EPUB files and HTTPS URLs from multiple `.txt` lists in one operation, use:

```bash
python -m ingest.cli --import-folder ./knowledge-to-import --allow-domain example.org --dry-run
```

The command scans subfolders, reads UTF-8 URL lists (one URL per line), and enforces the same explicit host allowlist and network safeguards as `--urls-file`. Remove `--dry-run` after configuring Open WebUI credentials. See [document import](advanced-import.md) for limits and folder layout.

## Prerequisites

Install dependencies and configure the API as described in the [README](../README.md#enable-rag). Create `urls.txt` with one HTTPS URL per line and optional `#` comments:

```text
https://example.org/article-a
https://example.org/article-b
```

```bash
python -m ingest.cli --urls-file urls.txt --allow-domain example.org --dry-run
python -m ingest.cli --url https://example.org/article-a --allow-domain example.org --dry-run
```

To index content, remove `--dry-run` after setting `OPEN_WEBUI_API_KEY` and `OPEN_WEBUI_KNOWLEDGE_ID`. URLs are deduplicated and changed pages are reprocessed based on text hashes. State is saved in `knowledge/.web-ingest.sqlite3`.

## Page discovery

```bash
python -m ingest.cli --url https://example.org/library/index --allow-domain example.org --crawl --max-depth 2 --max-pages 25 --dry-run
python -m ingest.cli --sitemap https://example.org/sitemap.xml --allow-domain example.org --max-pages 25 --dry-run
```

The crawler follows internal links within the starting URL's directory. Depth is restricted to 0–3, with up to 100 attempted pages per run. Sitemap discovery supports bounded XML sitemap indexes and also requires an allowlisted domain. `--crawl` requires a seed from `--url` or `--urls-file`; `--sitemap` alone does not activate additional crawling.

`--remote-pdf` imports **only the explicitly supplied PDF**, not all PDF links on a website:

```bash
python -m ingest.cli --remote-pdf https://example.org/book.pdf --allow-domain example.org --dry-run
```

## Safeguards and limits

- **HTTPS/443 and exact allowlist:** URL hosts must match `--allow-domain`; subdomains require separate authorization.
- **No redirects:** supply the final URL explicitly; non-global IP addresses are rejected and TLS verifies the host name.
- **Robots and pacing:** the collector checks `robots.txt`, honors disallow rules, and spaces requests.
- **Size limits:** HTML up to 2 MiB; remote PDF up to 30 MiB; URL list up to 100 entries; crawler up to 100 pages at maximum depth 3.
- **Not supported:** website login, JavaScript execution, `sitemap.xml.gz`, automatic PDF discovery, or bypassing access restrictions.

Respect licenses, authorization, and terms of service. `robots.txt` is not a reproduction license. `example.org` is illustrative; use an authorized domain instead. See [document extraction and OCR](advanced-import.md) and [reliability](reliability.md).
