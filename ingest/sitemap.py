"""Bounded sitemap URL discovery via the same HTTPS allowlisted fetcher."""
from collections import deque
from collections.abc import Iterable
from urllib.parse import urlsplit
from defusedxml import ElementTree
from .contracts import SourceFetcher
from .web import SourceRejected, normalized_url

def sitemap_urls(fetcher: SourceFetcher, start_urls: Iterable[str], *,
                 max_urls: int = 100, max_maps: int = 5) -> list[str]:
    if not 1 <= max_urls <= 100 or not 1 <= max_maps <= 10:
        raise ValueError("Sitemap limits exceeded")
    maps = deque(dict.fromkeys(normalized_url(url, fetcher.domains) for url in start_urls))
    queued_maps = set(maps)
    seen_maps: set[str] = set()
    pages: set[str] = set()
    while maps and len(seen_maps) < max_maps and len(pages) < max_urls:
        location = maps.popleft()
        if location in seen_maps:
            continue
        seen_maps.add(location)
        data = fetcher.get_resource(location, allowed_types=("xml",), max_bytes=2*1024*1024)
        try:
            root = ElementTree.fromstring(data)
        except ElementTree.ParseError as exc:
            raise SourceRejected("Invalid sitemap XML") from exc
        root_tag = root.tag.rsplit("}", 1)[-1]
        if root_tag not in ("urlset", "sitemapindex"):
            raise SourceRejected("Unexpected sitemap root element")
        for element in root:
            loc = next((child.text for child in element if child.tag.rsplit("}",1)[-1]=="loc"), None)
            if not loc:
                continue
            try:
                url = normalized_url(loc, fetcher.domains)
            except (SourceRejected, ValueError):
                continue
            if root_tag == "sitemapindex":
                if urlsplit(url).path.lower().endswith(".xml") and url not in queued_maps:
                    queued_maps.add(url)
                    maps.append(url)
            elif urlsplit(url).path.lower().endswith((".html", ".htm", "/")) or "." not in urlsplit(url).path.rsplit("/",1)[-1]:
                pages.add(url)
                if len(pages) >= max_urls:
                    break
    return sorted(pages)
