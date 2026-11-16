"""Bounded, same-site link discovery; never bypass SafeFetcher's SSRF/robots policies."""
from collections import deque
from collections.abc import Iterator
from html.parser import HTMLParser
from typing import cast
from urllib.parse import urljoin, urlsplit

from .contracts import CrawlItem, SourceFetcher
from .web import SourceRejected, normalized_url


class LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag != "a":
            return
        props = dict(attrs)
        if "nofollow" in cast(str, props.get("rel", "")).lower().split():
            return
        if props.get("href"):
            self.links.append(cast(str, props["href"]))


def discover_links(html: bytes, parent: str, domains: set[str], path_prefix: str) -> list[str]:
    parser = LinkParser()
    parser.feed(html.decode("utf-8", "replace"))
    found = []
    seen = set()
    for href in parser.links:
        try:
            candidate = normalized_url(urljoin(parent, href), domains)
            p = urlsplit(candidate)
            # Skip non-HTML resources and URLs outside the initial directory.
            if not p.path.startswith(path_prefix):
                continue
            if p.path.lower().endswith((".pdf", ".epub", ".zip", ".png", ".jpg", ".jpeg",
                                         ".gif", ".svg", ".mp4", ".xml", ".rss", ".json")):
                continue
            if candidate not in seen:
                seen.add(candidate)
                found.append(candidate)
        except (SourceRejected, ValueError):
            continue
    return found


def crawl(fetcher: SourceFetcher, seeds: list[str], max_pages: int = 25,
          max_depth: int = 2) -> Iterator[CrawlItem]:
    """Yield (url, html, error); errors are reported without killing the crawl.

    Each seed is restricted to its exact host and starting URL's directory;
    max_pages bounds attempted fetches, not just successful responses.
    """
    if not 1 <= max_pages <= 100 or not 0 <= max_depth <= 3:
        raise ValueError("max_pages must be 1..100 and max_depth 0..3")
    pending: deque[tuple[str, int, str | None, str]] = deque()
    seen = set()
    for seed in seeds:
        p = urlsplit(seed)
        prefix = p.path.rsplit("/", 1)[0] + "/"
        pending.append((seed, 0, p.hostname, prefix))
        seen.add(seed)
    count = 0
    while pending and count < max_pages:
        url, depth, host, prefix = pending.popleft()
        count += 1
        try:
            html = fetcher.get(url)
        except SourceRejected as exc:
            yield url, None, exc
            continue
        yield url, html, None
        if depth >= max_depth:
            continue
        for link in discover_links(html, url, fetcher.domains, prefix):
            if urlsplit(link).hostname != host or link in seen:
                continue
            seen.add(link)
            # Bound queue growth independently of the request count.
            if len(seen) <= max_pages * 12:
                pending.append((link, depth + 1, host, prefix))
