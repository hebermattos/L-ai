# Knowledge pipeline and evaluation

This operational guide supplements the [README](../README.md). No feature here requires a GPU. On a 16 GB CPU-only machine, keep concurrency, batch sizes, and OCR work bounded.

## Workflow

1. **Collect:** use authorized URLs, crawling, sitemaps, or PDF/EPUB documents. Run `--dry-run` before indexing. See [web ingestion](web-ingestion.md) and [document import](advanced-import.md).
2. **Extract and normalize:** Trafilatura for HTML, PyMuPDF for PDF, EbookLib for EPUB, and optional Tesseract OCR.
3. **Index:** configure `OPEN_WEBUI_API_KEY` and `OPEN_WEBUI_KNOWLEDGE_ID`; remove `--dry-run` to upload to Open WebUI Knowledge.
4. **Retrieve:** attach the knowledge base to the `lai` model/chat and ask specific questions. **Successful indexing does not prove that responses used retrieved documents.**
5. **Evaluate:** verify source attribution, fidelity, and retrieval using questions with documented answers.

## Metadata and provenance

HTML records the title, URL, and collection date. PDF records the title/author when present and page markers; EPUB retains declared title and author. Do not fabricate missing editions, translators, years, or page numbers. For comparative research, maintain any additional metadata in the source or a separate catalog.

## Incremental updates

Each run downloads permitted content, extracts text, and compares SHA-256 hashes. Unchanged documents are not reindexed, but **collection still generates HTTP traffic** (ETag/Last-Modified conditional requests are not supported). See [failure recovery](reliability.md) for interrupted operations.

## Optional scheduling

No schedule is installed by default. For cron, provide credentials through secure user-level configuration and prevent concurrent runs using `flock`. Example: every day at 03:00 (replace paths and domain):

```cron
0 3 * * * cd /home/USER/L-ai && /usr/bin/flock -n /tmp/lai-ingest.lock /home/USER/L-ai/.venv/bin/python -m ingest.cli --urls-file urls.txt --allow-domain example.org >> /home/USER/lai-ingest.log 2>&1
```

Cron typically does not inherit your interactive shell variables. Supply `OPEN_WEBUI_API_KEY` and `OPEN_WEBUI_KNOWLEDGE_ID` through private user/service configuration, not Git, public cron definitions, or CLI arguments. `flock` prevents concurrent imports into the same state database.

## Retrieval metrics

```bash
python -m ingest.evaluate tests/fixtures/retrieval_cases.json
```

The JSON contains `relevant_sources` and `retrieved_sources`; the evaluator computes `hit_at_k` and MRR from labeled sources. The included fixture is **synthetic**, demonstrates the expected format only, and does not establish real retrieval quality. Replace it with actual observed retrieval results from Open WebUI to compare methods.

Hybrid retrieval and reranking may be configured in Open WebUI **if supported by the installed version**. This project does not install external rerankers or a separate vector database. Evaluate real question sets and RAM usage before enabling additional models.

## Security and limits

Collect only authorized material, respecting copyright, licenses, and `robots.txt`. Documents and web pages are untrusted input; never treat embedded commands as user instructions. Process potentially malicious files in isolation. See [validation and limitations](reliability.md).
