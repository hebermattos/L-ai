"""HTTPS-only, IP-pinned, robots-aware fetcher. No redirects or private IPs."""
from __future__ import annotations

import ipaddress
import socket
import time
from urllib.parse import urlsplit, urlunsplit
from urllib.robotparser import RobotFileParser

import urllib3
from urllib3.util import Timeout


MAX_HTML_BYTES = 2 * 1024 * 1024
USER_AGENT = "L-ai-RAG-Ingest/1.0 (+local personal research)"


class SourceRejected(ValueError):
    pass


def normalized_url(url: str, domains: set[str]) -> str:
    value = url.strip()
    parsed = urlsplit(value)
    if parsed.scheme.lower() != "https" or not parsed.hostname:
        raise SourceRejected("Only HTTPS URLs are accepted")
    if parsed.username or parsed.password or parsed.port not in (None, 443):
        raise SourceRejected("Credentials and non-standard ports are forbidden")
    host = parsed.hostname.rstrip(".").lower()
    if not host or host not in domains:
        raise SourceRejected(f"Domain not allowlisted: {host}")
    if any(c in value for c in "\r\n\t\\") or len(value) > 2048:
        raise SourceRejected("Invalid or excessively long URL")
    if ipaddress_is_literal(host):
        raise SourceRejected("IP-literal hosts are forbidden")
    path = parsed.path or "/"
    return urlunsplit(("https", host, path, parsed.query, ""))


def ipaddress_is_literal(host: str) -> bool:
    try:
        ipaddress.ip_address(host)
        return True
    except ValueError:
        return False


def public_addresses(hostname: str) -> list[str]:
    """Reject entire DNS set if any resolution is not globally routable."""
    try:
        results = socket.getaddrinfo(hostname, 443, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise SourceRejected(f"DNS resolution failed: {hostname}") from exc
    ips = sorted({item[4][0] for item in results})
    if not ips or any(not ipaddress.ip_address(ip).is_global for ip in ips):
        raise SourceRejected("DNS contains private, loopback, or non-global addresses")
    return ips


class SafeFetcher:
    def __init__(self, domains: set[str], max_bytes: int = MAX_HTML_BYTES, pause: float = 2.0):
        self.domains = {d.strip().lower().rstrip(".") for d in domains if d.strip()}
        if not self.domains:
            raise ValueError("At least one explicit allowed domain is required")
        self.max_bytes = max_bytes
        self.pause = pause
        self._robots: dict[str, RobotFileParser | None] = {}
        self._last_call = 0.0

    def _fetch(self, url: str, *, check_type: bool = True) -> tuple[int, bytes]:
        parsed = urlsplit(url)
        ips = public_addresses(parsed.hostname)
        # Connect to a vetted IP, use the original hostname for SNI and certificate validation.
        # No redirect following; DNS cannot change between validation and TCP connect.
        wait = self.pause - (time.monotonic() - self._last_call)
        if wait > 0:
            time.sleep(wait)
        self._last_call = time.monotonic()
        pool = urllib3.HTTPSConnectionPool(
            ips[0], port=443, server_hostname=parsed.hostname,
            assert_hostname=parsed.hostname, cert_reqs="CERT_REQUIRED",
            timeout=Timeout(connect=5, read=15), retries=False,
            maxsize=1, block=True,
        )
        target = parsed.path or "/"
        if parsed.query:
            target += "?" + parsed.query
        response = None
        try:
            response = pool.urlopen(
                "GET", target, headers={"Host": parsed.hostname, "User-Agent": USER_AGENT,
                                       "Accept": "text/html,text/plain;q=0.9"},
                preload_content=False, redirect=False, retries=False,
            )
            if response.status in (301, 302, 303, 307, 308):
                raise SourceRejected("HTTP redirects are disabled: add the destination explicitly")
            if response.status not in (200, 404):
                raise SourceRejected(f"Unexpected HTTP status: {response.status}")
            if check_type and response.status == 200:
                ctype = response.headers.get("Content-Type", "").split(";")[0].lower().strip()
                if ctype not in ("text/html", "application/xhtml+xml", "text/plain"):
                    raise SourceRejected(f"Unsupported content type: {ctype}")
            if response.status == 404:
                return 404, b""
            payload = response.read(self.max_bytes + 1, decode_content=True)
            if len(payload) > self.max_bytes:
                raise SourceRejected("Response exceeds byte limit")
            return response.status, payload
        except urllib3.exceptions.HTTPError as exc:
            raise SourceRejected(f"HTTPS request failed: {type(exc).__name__}") from exc
        finally:
            if response is not None:
                response.release_conn()
            pool.close()

    def permitted(self, url: str) -> bool:
        parsed = urlsplit(url)
        host = parsed.hostname
        if host not in self._robots:
            robots_url = f"https://{host}/robots.txt"
            try:
                status, data = self._fetch(robots_url, check_type=False)
                parser = RobotFileParser()
                if status == 404:
                    parser.parse([])
                else:
                    parser.parse(data.decode("utf-8", errors="replace").splitlines())
                self._robots[host] = parser
            except SourceRejected:
                # Fail closed when robots rules cannot be checked.
                self._robots[host] = None
        parser = self._robots[host]
        return parser is not None and parser.can_fetch(USER_AGENT, url)

    def get(self, url: str) -> bytes:
        safe = normalized_url(url, self.domains)
        if not self.permitted(safe):
            raise SourceRejected("robots.txt disallows access or is unavailable")
        status, data = self._fetch(safe)
        if status != 200:
            raise SourceRejected(f"Page unavailable: {status}")
        return data
