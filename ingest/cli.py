"""Bounded ingestion of explicit HTTPS pages, site links and local documents."""
from __future__ import annotations

import argparse
from collections.abc import Iterable, Iterator, Sequence
from contextlib import ExitStack
from dataclasses import dataclass
from datetime import datetime, timezone
import os
from pathlib import Path
from typing import cast
import sys

import trafilatura

from .contracts import CrawlItem, SourceFetcher
from .crawler import crawl
from .sitemap import sitemap_urls
from .remote import read_remote_pdf
from .documents import DocumentError, file_paths, format_document, read_document
from .folder import discover_import_folder
from .manifests import read_url_lines
from .service import ingest_page
from .state import IngestState
from .web import SafeFetcher, SourceRejected, normalized_url
from .webui import WebUI, WebUIError


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
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
    p.add_argument("--import-folder", type=Path, help="Import PDF/EPUB files and separate urls.txt/crawl.txt URL lists")
    p.add_argument("--max-documents", type=int, default=50)
    p.add_argument("--ocr", action="store_true", help="Use local Tesseract only for scanned PDF pages")
    knowledge = p.add_mutually_exclusive_group()
    knowledge.add_argument("--knowledge-id", help="Target base ID; overrides OPEN_WEBUI_KNOWLEDGE_ID")
    knowledge.add_argument("--knowledge-name", help="Exact, unique base name; overrides the environment ID")
    p.add_argument("--webui-url", default="http://127.0.0.1:3000")
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--state", type=Path, default=Path("knowledge/.web-ingest.sqlite3"))
    p.add_argument("--max-urls", type=int, default=25)
    args = p.parse_args(argv)
    if args.knowledge_id is None and args.knowledge_name is None:
        args.knowledge_id = os.getenv("OPEN_WEBUI_KNOWLEDGE_ID", "")
    return args


def list_urls(args: argparse.Namespace, extra_urls: Iterable[str] = ()) -> list[str]:
    urls = list(args.url) + list(extra_urls)
    if args.urls_file:
        if args.urls_file.stat().st_size > 65536:
            raise ValueError("URL list exceeds 64 KiB")
        urls.extend(read_url_lines(args.urls_file))
    if not 1 <= args.max_urls <= 100 or len(urls) > args.max_urls:
        raise ValueError("URL count outside allowed range")
    if urls and not args.allow_domain:
        raise ValueError("--allow-domain is required for web URLs")
    return list(dict.fromkeys(normalized_url(u, set(args.allow_domain)) for u in urls))


def extract_markdown(url: str, html: bytes) -> tuple[str, str]:
    body = trafilatura.extract(html, output_format="markdown", include_links=False, include_comments=False)
    if not body or len(body.strip()) < 100:
        raise ValueError("No substantial readable text found")
    metadata = trafilatura.extract_metadata(html)
    title = (metadata.title if metadata and metadata.title else url).replace("\n", " ").strip()
    return title, body.strip()


def format_doc(url: str, title: str, body: str) -> str:
    return (f"# {title}\n\nOriginal source: {url}\n"
            f"Collected on: {datetime.now(timezone.utc).date().isoformat()}\n\n{body}\n")


@dataclass(frozen=True)
class IngestPlan:
    urls: list[str]
    crawl_targets: set[str]
    documents: list[Path]


def prepare_inputs(args: argparse.Namespace) -> IngestPlan:
    """Discover and validate inputs without creating API or state resources."""
    folder_documents, folder_urls, folder_crawl_urls = (
        discover_import_folder(args.import_folder)
        if args.import_folder else ([], [], []))
    # Validate all seeds together to enforce one shared URL limit.
    urls = list_urls(args, folder_urls + folder_crawl_urls)
    crawl_targets = {
        normalized_url(url, set(args.allow_domain)) for url in folder_crawl_urls
    }
    manual_crawl_seeds = set(list_urls(args)) if args.crawl else set()
    if args.crawl and not manual_crawl_seeds:
        raise ValueError("--crawl requires a seed from --url or --urls-file")
    crawl_targets.update(manual_crawl_seeds)
    documents = file_paths(args.file + folder_documents, args.directory, args.max_documents)
    if args.sitemap or args.remote_pdf:
        if not args.allow_domain:
            raise ValueError("--allow-domain required for remote resources")
        for remote_url in args.sitemap + args.remote_pdf:
            normalized_url(remote_url, set(args.allow_domain))
    if args.sitemap and not 1 <= args.max_pages <= 100:
        raise ValueError("Invalid sitemap max-pages")
    if not urls and not documents and not args.sitemap and not args.remote_pdf:
        raise ValueError("Provide --url, --urls-file, --file, --directory, or --import-folder with supported content")
    if len(crawl_targets) > args.max_pages:
        raise ValueError("Crawler seed count exceeds --max-pages")
    if not 1 <= args.max_pages <= 100 or not 0 <= args.max_depth <= 3:
        raise ValueError("--max-pages must be 1..100 and --max-depth 0..3")
    return IngestPlan(urls, crawl_targets, documents)


def execute_sources(args: argparse.Namespace, plan: IngestPlan,
                    fetcher: SourceFetcher | None, webui: WebUI | None,
                    state: IngestState | None) -> int:
    """Process prepared sources in the existing order and report failures."""
    urls, crawl_targets, documents = plan.urls, plan.crawl_targets, plan.documents
    failed = 0
    source_fetcher = cast(SourceFetcher, fetcher)

    def process(source: str, title: str, body: str, formatted: str) -> None:
        if args.dry_run:
            print(f"DRY RUN {source}: {title} ({len(body)} chars)")
        else:
            result = ingest_page(cast(IngestState, state), cast(WebUI, webui),
                                 source, title, body, formatted)
            print(f"{result} {source}")

    def explicit_pages(direct_urls: list[str]) -> Iterator[CrawlItem]:
        for url in direct_urls:
            try:
                yield url, source_fetcher.get(url), None
            except SourceRejected as exc:
                yield url, None, exc

    if args.sitemap:
        try:
            urls = list(dict.fromkeys(urls + sitemap_urls(source_fetcher, args.sitemap, max_urls=args.max_pages)))
        except (SourceRejected, ValueError, OSError) as exc:
            failed += 1
            print(f"FAILED sitemap: {exc}", file=sys.stderr)
    # The two input lists have independent behavior within the same run.
    # URLs appearing in both lists are crawled once rather than fetched twice.
    direct_urls = [url for url in urls if url not in crawl_targets]
    crawl_seeds = [url for url in urls if url in crawl_targets]
    sources: Iterator[CrawlItem] = explicit_pages(direct_urls)
    if crawl_seeds:
        from itertools import chain
        sources = chain(sources, crawl(source_fetcher, crawl_seeds, args.max_pages, args.max_depth))
    if urls:
        for item in sources:
            try:
                url, html, error = item
                if error:
                    raise error
                title, body = extract_markdown(url, cast(bytes, html))
                process(url, title, body, format_doc(url, title, body))
            except (SourceRejected, ValueError, WebUIError, OSError) as exc:
                failed += 1
                print(f"FAILED web page: {exc}", file=sys.stderr)
    for remote_url in args.remote_pdf:
        try:
            doc = read_remote_pdf(source_fetcher, remote_url)
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
    return 1 if failed else 0


def run(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        plan = prepare_inputs(args)
    except (ValueError, OSError) as exc:
        print(f"Invalid input: {exc}", file=sys.stderr)
        return 2

    if not args.dry_run and (not os.getenv("OPEN_WEBUI_API_KEY")
                            or not (args.knowledge_id or args.knowledge_name)):
        print("Set OPEN_WEBUI_API_KEY and select --knowledge-id, --knowledge-name, or OPEN_WEBUI_KNOWLEDGE_ID", file=sys.stderr)
        return 2

    fetcher = SafeFetcher(set(args.allow_domain)) if plan.urls or args.sitemap or args.remote_pdf else None
    with ExitStack() as resources:
        webui = state = None
        if not args.dry_run:
            try:
                webui = WebUI(args.webui_url, os.environ["OPEN_WEBUI_API_KEY"], args.knowledge_id)
                resources.callback(webui.close)
                if args.knowledge_name is not None:
                    webui.knowledge_id = webui.resolve_knowledge(args.knowledge_name)
            except (ValueError, WebUIError) as exc:
                print(f"Knowledge selection failed: {exc}", file=sys.stderr)
                return 2
            state = IngestState(args.state)
            resources.callback(state.close)
        return execute_sources(args, plan, fetcher, webui, state)


if __name__ == "__main__":
    sys.exit(run())

