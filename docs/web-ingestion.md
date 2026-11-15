# Web ingestion for RAG

This guide covers the **currently implemented** features: individual HTTPS URLs, `urls.txt` lists, bounded authorized recursive crawling, sitemap discovery and explicitly supplied remote PDFs. HTML is extracted with Trafilatura and can be uploaded to an Open WebUI Knowledge Base.

## Prerequisites

Install dependencies and configure API access as shown in the [README](../README.md#enable-rag). Create `urls.txt` with one HTTPS URL per line; lines starting with `#` are comments:

```text
https://example.org/article-a
https://example.org/article-b
```

```bash
python -m ingest.cli --urls-file urls.txt --allow-domain example.org --dry-run
python -m ingest.cli --url https://example.org/article-a --allow-domain example.org --dry-run
```

Remove `--dry-run` only after defining `OPEN_WEBUI_API_KEY` and `OPEN_WEBUI_KNOWLEDGE_ID`. URLs are deduplicated; changed pages are reprocessed based on text hashes. State is stored in `biblioteca/.web-ingest.sqlite3`.

## Page discovery

```bash
python -m ingest.cli --url https://example.org/library/index --allow-domain example.org --crawl --max-depth 2 --max-pages 25 --dry-run
python -m ingest.cli --sitemap https://example.org/sitemap.xml --allow-domain example.org --max-pages 25 --dry-run
```

The crawler follows only in-directory links on the seed URL's host, with a depth of 0–3 and up to 100 attempted pages per run. Sitemap discovery supports bounded XML sitemap indexes; it does not follow arbitrary links and requires an authorized domain. `--crawl` requires an HTTPS seed from `--url` or `--urls-file`; `--sitemap` alone does not enable additional crawling.

`--remote-pdf` imports **only the explicitly supplied PDF**, not every PDF linked on a site:

```bash
python -m ingest.cli --remote-pdf https://example.org/book.pdf --allow-domain example.org --dry-run
```

## Safeguards and limits

- **HTTPS/443 and exact host allowlist:** the URL host must match `--allow-domain`; authorize subdomains separately.
- **No redirects:** supply the final URL explicitly. Non-global IP addresses are refused and TLS verifies the host name.
- **Robots and rate limits:** the fetcher respects `robots.txt`, fails closed for disallowed resources and pauses between requests.
- **Size/volume:** HTML up to 2 MiB, remote PDFs up to 30 MiB, URL lists up to 100 entries, crawler up to 100 pages and maximum depth 3.
- **Not included:** site login, JavaScript execution, `sitemap.xml.gz`, automatic PDF discovery or bypassing access restrictions.

Respect licenses, permission and terms of use. `robots.txt` permission is not a reproduction license. `example.org` is illustrative; use an authorized source. See [documents and OCR](advanced-import.md) and [reliability details](reliability.md).
