# Knowledge pipeline and evaluation

This operations guide complements the [README](../README.md). No workflow below requires a GPU. For 16 GB RAM and CPU-only systems, keep concurrency, batch sizes and OCR usage bounded.

## Workflow

1. **Collect:** authorized URLs, crawler pages, sitemaps, PDFs or EPUBs. Run `--dry-run` before indexing. See [web ingestion](web-ingestion.md) and [documents](advanced-import.md).
2. **Extract and normalize:** Trafilatura (HTML), PyMuPDF (PDF), EbookLib (EPUB), and optionally Tesseract (OCR).
3. **Index:** set `OPEN_WEBUI_API_KEY` and `OPEN_WEBUI_KNOWLEDGE_ID`; remove `--dry-run` to upload to Open WebUI Knowledge.
4. **Retrieve:** attach the knowledge base to the `lai` model/chat and ask source-specific questions. **Successful indexing does not prove the answer used retrieved content.**
5. **Evaluate:** verify attribution, faithfulness and retrieval against questions with documented answers.

## Metadata and provenance

HTML pages retain the title, URL and collection date. PDFs retain title/author when available and page markers; EPUB retains declared title/author metadata. Do not invent editions, translators, years or page numbers. For bibliographic comparison, maintain any missing information in the source or a separate catalog.

## Incremental updates

Each run downloads allowed content, extracts text, and compares SHA-256 content hashes. Unchanged documents avoid reindexing; **requests still generate HTTP traffic** (no ETag/Last-Modified support). See [recovery](reliability.md) if a run fails.

## Optional scheduling

No schedule is installed by default. For cron, supply credentials through a private user/service environment and use `flock` to avoid concurrent runs. Example: daily at 03:00; replace paths and allowed domain:

```cron
0 3 * * * cd /home/USER/L-ai && /usr/bin/flock -n /tmp/lai-ingest.lock /home/USER/L-ai/.venv/bin/python -m ingest.cli --urls-file urls.txt --allow-domain example.org >> /home/USER/lai-ingest.log 2>&1
```

Cron does not normally inherit your shell variables. Provide `OPEN_WEBUI_API_KEY` and `OPEN_WEBUI_KNOWLEDGE_ID` securely, not in Git, public cron definitions or CLI arguments. `flock` protects the local state database from competing ingestion processes.

## Retrieval metrics

```bash
python -m ingest.evaluate tests/fixtures/retrieval_cases.json
```

The JSON supplies `relevant_sources` and `retrieved_sources`. Evaluation reports `hit_at_k` and MRR against labeled sources. The fixture is **synthetic**, only demonstrating the format; it does not establish actual model or knowledge-base quality. For retrieval comparisons, replace it with measured Open WebUI retrieval results.

Hybrid search and reranking can be enabled **if your installed Open WebUI version supports them**. No external reranker or alternative vector database is included. Measure improvements against real questions and watch RAM usage before adding models.

## Security and limits

Collect only authorized material, respecting licensing, copyright and `robots.txt`. Treat website and document content as untrusted data, not instructions. Isolate processing of potentially malicious files. See [validation and limits](reliability.md).
