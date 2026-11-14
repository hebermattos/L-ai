"""Bounded ingestion of explicit HTTPS pages, site links and local documents."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import os
from pathlib import Path
import sys

import trafilatura

from .crawler import crawl
from .sitemap import sitemap_urls
from .remote import read_remote_pdf
from .documents import DocumentError, file_paths, format_document, read_document
from .service import ingest_page
from .state import IngestState
from .web import SafeFetcher, SourceRejected, normalized_url
from .webui import WebUI, WebUIError


def parse_args(argv=None):
    p = argparse.ArgumentParser(description="L-ai: approved web pages and local documents -> Open WebUI RAG")
    p.add_argument("--url", action="append", default=[])
    p.add_argument("--urls-file", type=Path)
    p.add_argument("--allow-domain", action="append", default=[])
    p.add_argument("--crawl", action="store_true", help="Follow allowed same-directory HTML links")
    p.add_argument("--sitemap", action="append", default=[], help="Authorized sitemap XML URL (repeatable)")
    p.add_argument("--remote-pdf", action="append", default=[], help="Explicit authorized PDF URL (repeatable)")
    p.add_argument("--max-depth", type=int, default=2)
    p.add_argument("--max-pages", type=int, default=25)
    p.add_argument("--file", type=Path, action="append", default=[])
    p.add_argument("--directory", type=Path)
    p.add_argument("--max-documents", type=int, default=50)
    p.add_argument("--ocr", action="store_true", help="Use local Tesseract only for scanned PDF pages")
    p.add_argument("--knowledge-id", default=os.getenv("OPEN_WEBUI_KNOWLEDGE_ID", ""))
    p.add_argument("--webui-url", default="http://127.0.0.1:3000")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--state", type=Path, default=Path("biblioteca/.web-ingest.sqlite3"))
    p.add_argument("--max-urls", type=int, default=25)
    return p.parse_args(argv)


def list_urls(args):
    urls = list(args.url)
    if args.urls_file:
        if args.urls_file.stat().st_size > 65536:
            raise ValueError("URL list exceeds 64 KiB")
        urls.extend(line.strip() for line in args.urls_file.read_text(encoding="utf-8").splitlines()
                    if line.strip() and not line.lstrip().startswith("#"))
    if not 1 <= args.max_urls <= 100 or len(urls) > args.max_urls:
        raise ValueError("URL count outside allowed range")
    if urls and not args.allow_domain:
        raise ValueError("--allow-domain is required for web URLs")
    return list(dict.fromkeys(normalized_url(u, set(args.allow_domain)) for u in urls))


def extract_markdown(url, html):
    body = trafilatura.extract(html, output_format="markdown", include_links=False, include_comments=False)
    if not body or len(body.strip()) < 100:
        raise ValueError("No substantial readable text found")
    metadata = trafilatura.extract_metadata(html)
    title = (metadata.title if metadata and metadata.title else url).replace("\n", " ").strip()
    return title, body.strip()


def format_doc(url, title, body):
    return (f"# {title}\n\nFonte original: {url}\n"
            f"Coletado em: {datetime.now(timezone.utc).date().isoformat()}\n\n{body}\n")


def run(argv=None):
    args = parse_args(argv)
    try:
        urls = list_urls(args)
        documents = file_paths(args.file, args.directory, args.max_documents)
        if args.sitemap or args.remote_pdf:
            if not args.allow_domain:
                raise ValueError("--allow-domain required for remote resources")
            for remote_url in args.sitemap + args.remote_pdf:
                normalized_url(remote_url, set(args.allow_domain))
        if args.sitemap and not 1 <= args.max_pages <= 100:
            raise ValueError("Invalid sitemap max-pages")
        if not urls and not documents and not args.sitemap and not args.remote_pdf:
            raise ValueError("Provide --url, --urls-file, --file, or --directory")
        if args.crawl and not urls:
            raise ValueError("--crawl requires an HTTPS seed")
        if args.crawl and len(urls) > args.max_pages:
            raise ValueError("Seed count exceeds --max-pages")
        if not 1 <= args.max_pages <= 100 or not 0 <= args.max_depth <= 3:
            raise ValueError("--max-pages must be 1..100 and --max-depth 0..3")
    except (ValueError, OSError) as exc:
        print(f"Invalid input: {exc}", file=sys.stderr)
        return 2

    if not args.dry_run and (not os.getenv("OPEN_WEBUI_API_KEY") or not args.knowledge_id):
        print("Set OPEN_WEBUI_API_KEY and OPEN_WEBUI_KNOWLEDGE_ID", file=sys.stderr)
        return 2

    fetcher = SafeFetcher(set(args.allow_domain)) if urls or args.sitemap or args.remote_pdf else None
    webui = None if args.dry_run else WebUI(args.webui_url, os.environ["OPEN_WEBUI_API_KEY"], args.knowledge_id)
    state = None if args.dry_run else IngestState(args.state)
    failed = 0

    def process(source, title, body, formatted):
        if args.dry_run:
            print(f"DRY RUN {source}: {title} ({len(body)} chars)")
        else:
            print(f"{ingest_page(state, webui, source, title, body, formatted)} {source}")

    def explicit_pages():
        for url in urls:
            try:
                yield url, fetcher.get(url), None
            except SourceRejected as exc:
                yield url, None, exc

    try:
        if args.sitemap:
            try:
                urls = list(dict.fromkeys(urls + sitemap_urls(fetcher, args.sitemap, max_urls=args.max_pages)))
            except (SourceRejected, ValueError, OSError) as exc:
                failed += 1
                print(f"FAILED sitemap: {exc}", file=sys.stderr)
        if urls:
            sources = (crawl(fetcher, urls, args.max_pages, args.max_depth)
                       if args.crawl else explicit_pages())
            for item in sources:
                try:
                    url, html, error = item
                    if error:
                        raise error
                    title, body = extract_markdown(url, html)
                    process(url, title, body, format_doc(url, title, body))
                except (SourceRejected, ValueError, WebUIError, OSError) as exc:
                    failed += 1
                    print(f"FAILED web page: {exc}", file=sys.stderr)
        for remote_url in args.remote_pdf:
            try:
                doc = read_remote_pdf(fetcher, remote_url)
                process(doc.source, doc.title, doc.body, format_document(doc))
            except (SourceRejected, DocumentError, ValueError, WebUIError, OSError) as exc:
                failed += 1
                print(f"FAILED remote PDF: {exc}", file=sys.stderr)
        for path in documents:
            try:
                doc = read_document(path, ocr=args.ocr)
                process(doc.source, doc.title, doc.body, format_document(doc))
            except (DocumentError, ValueError, WebUIError, OSError) as exc:
                failed += 1
                print(f"FAILED {path.name}: {exc}", file=sys.stderr)
    finally:
        if state:
            state.close()
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(run())
