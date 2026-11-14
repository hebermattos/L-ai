"""One-off allowed-domain scraping and Open WebUI knowledge ingestion."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import sys

import trafilatura

from .web import SafeFetcher, SourceRejected, normalized_url
from .webui import WebUI, WebUIError


def parse_args(argv=None):
    p = argparse.ArgumentParser(description="L-ai: approved HTTPS pages -> Open WebUI RAG")
    p.add_argument("--url", action="append", default=[], help="Individual HTTPS URL (repeatable)")
    p.add_argument("--urls-file", type=Path, help="UTF-8 text file, one URL per line")
    p.add_argument("--allow-domain", action="append", required=True, help="Exact authorized hostname; repeatable")
    p.add_argument("--knowledge-id", default=os.getenv("OPEN_WEBUI_KNOWLEDGE_ID", ""))
    p.add_argument("--webui-url", default="http://127.0.0.1:3000")
    p.add_argument("--dry-run", action="store_true", help="Extract only; never upload")
    p.add_argument("--state", type=Path, default=Path("biblioteca/.web-ingest.sqlite3"))
    p.add_argument("--max-urls", type=int, default=25)
    return p.parse_args(argv)


def list_urls(args) -> list[str]:
    urls = list(args.url)
    if args.urls_file:
        if args.urls_file.stat().st_size > 65536:
            raise ValueError("URL list exceeds 64 KiB")
        urls.extend(line.strip() for line in args.urls_file.read_text(encoding="utf-8").splitlines()
                    if line.strip() and not line.lstrip().startswith("#"))
    if not urls:
        raise ValueError("Provide --url or --urls-file")
    if not 1 <= args.max_urls <= 100:
        raise ValueError("--max-urls must be 1..100")
    if len(urls) > args.max_urls:
        raise ValueError("Too many URLs for this run")
    return list(dict.fromkeys(normalized_url(u, set(args.allow_domain)) for u in urls))


def extract_markdown(url: str, html: bytes) -> tuple[str, str]:
    body = trafilatura.extract(html, output_format="markdown", include_links=False, include_comments=False)
    if not body or len(body.strip()) < 100:
        raise ValueError("No substantial readable text found")
    metadata = trafilatura.extract_metadata(html)
    title = (metadata.title if metadata and metadata.title else url).replace("\n", " ").strip()
    return title, body.strip()


def format_doc(url: str, title: str, body: str) -> str:
    return (f"# {title}\n\nFonte original: {url}\n"
            f"Coletado em: {datetime.now(timezone.utc).date().isoformat()}\n\n{body}\n")


def run(argv=None) -> int:
    args = parse_args(argv)
    try:
        urls = list_urls(args)
    except (ValueError, OSError) as exc:
        print(f"Invalid input: {exc}", file=sys.stderr)
        return 2

    if not args.dry_run and (not os.getenv("OPEN_WEBUI_API_KEY") or not args.knowledge_id):
        print("Set OPEN_WEBUI_API_KEY and --knowledge-id (or OPEN_WEBUI_KNOWLEDGE_ID)", file=sys.stderr)
        return 2
    fetcher = SafeFetcher(set(args.allow_domain))
    webui = None if args.dry_run else WebUI(args.webui_url, os.environ["OPEN_WEBUI_API_KEY"], args.knowledge_id)
    db = None
    if not args.dry_run:
        args.state.parent.mkdir(parents=True, exist_ok=True)
        db = sqlite3.connect(args.state)
        db.execute("CREATE TABLE IF NOT EXISTS pages (url TEXT PRIMARY KEY, hash TEXT NOT NULL, file_id TEXT NOT NULL, knowledge_id TEXT NOT NULL)")
        db.execute("CREATE INDEX IF NOT EXISTS pages_hash ON pages (hash, knowledge_id)")
    failed = 0
    for url in urls:
        try:
            html = fetcher.get(url)
            title, body = extract_markdown(url, html)
            content_hash = hashlib.sha256(body.encode("utf-8")).hexdigest()
            name = hashlib.sha256(url.encode("utf-8")).hexdigest()[:20] + ".md"
            if args.dry_run:
                print(f"DRY RUN {url}: {title} ({len(body)} chars)")
                continue
            old = db.execute("SELECT hash, file_id FROM pages WHERE url=? AND knowledge_id=?", (url, args.knowledge_id)).fetchone()
            if old and old[0] == content_hash:
                print(f"UNCHANGED {url}")
                continue
            duplicate = db.execute("SELECT file_id FROM pages WHERE hash=? AND knowledge_id=?",
                                   (content_hash, args.knowledge_id)).fetchone()
            if duplicate and not old:
                print(f"DUPLICATE CONTENT {url}")
                continue
            document = format_doc(url, title, body)
            if old:
                webui.update_content(old[1], document)
                file_id = old[1]
                action = "UPDATED"
            else:
                file_id = webui.upload(name, document)
                webui.wait_indexed(file_id)
                webui.add_to_knowledge(file_id)
                action = "IMPORTED"
            db.execute("INSERT OR REPLACE INTO pages(url, hash, file_id, knowledge_id) VALUES (?, ?, ?, ?)",
                       (url, content_hash, file_id, args.knowledge_id))
            db.commit()
            print(f"{action} {url}")
        except (SourceRejected, ValueError, WebUIError, OSError) as exc:
            failed += 1
            print(f"FAILED {url}: {exc}", file=sys.stderr)
    if db:
        db.close()
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(run())
