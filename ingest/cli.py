"""Import explicit allowlisted HTTPS URLs to Open WebUI's Knowledge Base."""
import argparse
from datetime import datetime, timezone
import os
from pathlib import Path
import sys
import trafilatura
from .service import ingest_page
from .state import IngestState
from .web import SafeFetcher, SourceRejected, normalized_url
from .webui import WebUI, WebUIError

def parse_args(argv=None):
    p = argparse.ArgumentParser(description="L-ai: approved HTTPS pages -> Open WebUI RAG")
    p.add_argument("--url",action="append",default=[])
    p.add_argument("--urls-file",type=Path)
    p.add_argument("--allow-domain",action="append",required=True)
    p.add_argument("--knowledge-id",default=os.getenv("OPEN_WEBUI_KNOWLEDGE_ID",""))
    p.add_argument("--webui-url",default="http://127.0.0.1:3000")
    p.add_argument("--dry-run",action="store_true")
    p.add_argument("--state",type=Path,default=Path("biblioteca/.web-ingest.sqlite3"))
    p.add_argument("--max-urls",type=int,default=25)
    return p.parse_args(argv)

def list_urls(args):
    urls = list(args.url)
    if args.urls_file:
        if args.urls_file.stat().st_size > 65536:
            raise ValueError("URL list exceeds 64 KiB")
        urls.extend(line.strip() for line in args.urls_file.read_text(encoding="utf-8").splitlines()
                    if line.strip() and not line.lstrip().startswith("#"))
    if not urls:
        raise ValueError("Provide --url or --urls-file")
    if not 1 <= args.max_urls <= 100 or len(urls)>args.max_urls:
        raise ValueError("URL count outside allowed range")
    return list(dict.fromkeys(normalized_url(u,set(args.allow_domain)) for u in urls))

def extract_markdown(url,html):
    body = trafilatura.extract(html,output_format="markdown",include_links=False,include_comments=False)
    if not body or len(body.strip())<100:
        raise ValueError("No substantial readable text found")
    metadata = trafilatura.extract_metadata(html)
    title = (metadata.title if metadata and metadata.title else url).replace("\n"," ").strip()
    return title,body.strip()

def format_doc(url,title,body):
    return (f"# {title}\n\nFonte original: {url}\n"
            f"Coletado em: {datetime.now(timezone.utc).date().isoformat()}\n\n{body}\n")

def run(argv=None):
    args = parse_args(argv)
    try:
        urls = list_urls(args)
    except (ValueError,OSError) as exc:
        print(f"Invalid input: {exc}",file=sys.stderr)
        return 2
    if not args.dry_run and (not os.getenv("OPEN_WEBUI_API_KEY") or not args.knowledge_id):
        print("Set OPEN_WEBUI_API_KEY and OPEN_WEBUI_KNOWLEDGE_ID",file=sys.stderr)
        return 2
    fetcher = SafeFetcher(set(args.allow_domain))
    webui = None if args.dry_run else WebUI(args.webui_url,os.environ["OPEN_WEBUI_API_KEY"],args.knowledge_id)
    state = None if args.dry_run else IngestState(args.state)
    failed = 0
    try:
        for url in urls:
            try:
                html = fetcher.get(url)
                title,body = extract_markdown(url,html)
                if args.dry_run:
                    print(f"DRY RUN {url}: {title} ({len(body)} chars)")
                    continue
                action = ingest_page(state,webui,url,title,body,format_doc(url,title,body))
                print(f"{action} {url}")
            except (SourceRejected,ValueError,WebUIError,OSError) as exc:
                failed+=1
                print(f"FAILED {url}: {exc}",file=sys.stderr)
    finally:
        if state:
            state.close()
    return 1 if failed else 0

if __name__=="__main__":
    sys.exit(run())
