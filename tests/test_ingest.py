import argparse
import pathlib
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from ingest.cli import list_urls
from ingest.web import SafeFetcher, SourceRejected, normalized_url, public_addresses
from ingest.webui import WebUI


DOMAINS = {"example.org"}


class UrlSafetyTests(unittest.TestCase):
    def test_https_allowlist_and_fragment(self):
        self.assertEqual(normalized_url("https://example.org/x#frag", DOMAINS), "https://example.org/x")

    def test_rejects_unsafe_urls(self):
        for url in (
            "http://example.org/", "https://127.0.0.1/", "https://localhost/",
            "https://example.org.evil.test/", "https://user:pw@example.org/",
            "https://example.org:8443/", "file:///etc/passwd", "https://example.org\\@other.test/",
        ):
            with self.subTest(url=url), self.assertRaises(SourceRejected):
                normalized_url(url, DOMAINS)

    @patch("ingest.web.socket.getaddrinfo")
    def test_dns_rejects_mixed_public_private(self, getaddrinfo):
        getaddrinfo.return_value = [(None, None, None, None, ("8.8.8.8", 443)),
                                    (None, None, None, None, ("127.0.0.1", 443))]
        with self.assertRaises(SourceRejected):
            public_addresses("example.org")

    @patch("ingest.web.socket.getaddrinfo")
    def test_public_only_dns(self, getaddrinfo):
        getaddrinfo.return_value = [(None, None, None, None, ("8.8.8.8", 443))]
        self.assertEqual(public_addresses("example.org"), ["8.8.8.8"])

    def test_robots_disallow(self):
        fetcher = SafeFetcher(DOMAINS, pause=0)
        fetcher._fetch = MagicMock(return_value=(200, b"User-agent: *\nDisallow: /private"))
        self.assertFalse(fetcher.permitted("https://example.org/private/page"))
        self.assertTrue(fetcher.permitted("https://example.org/allowed"))

    def test_robots_error_fails_closed(self):
        fetcher = SafeFetcher(DOMAINS, pause=0)
        fetcher._fetch = MagicMock(side_effect=SourceRejected("down"))
        self.assertFalse(fetcher.permitted("https://example.org/"))

    def test_redirect_rejected_and_ip_pinned(self):
        fetcher = SafeFetcher(DOMAINS, pause=0)
        with patch("ingest.web.public_addresses", return_value=["8.8.8.8"]), patch("ingest.web.urllib3.HTTPSConnectionPool") as pool:
            response = MagicMock(status=302)
            pool.return_value.urlopen.return_value = response
            with self.assertRaises(SourceRejected):
                fetcher._fetch("https://example.org/page")
            self.assertEqual(pool.call_args.args[0], "8.8.8.8")
            self.assertEqual(pool.call_args.kwargs["assert_hostname"], "example.org")

    def test_maximum_response_size(self):
        fetcher = SafeFetcher(DOMAINS, max_bytes=5, pause=0)
        with patch("ingest.web.public_addresses", return_value=["8.8.8.8"]), patch("ingest.web.urllib3.HTTPSConnectionPool") as pool:
            response = MagicMock(status=200)
            response.headers = {"Content-Type": "text/html"}
            response.read.return_value = b"123456"
            pool.return_value.urlopen.return_value = response
            with self.assertRaises(SourceRejected):
                fetcher._fetch("https://example.org/")

    def test_url_list_deduplicated(self):
        with tempfile.TemporaryDirectory() as directory:
            file = pathlib.Path(directory) / "urls.txt"
            file.write_text("# comment\nhttps://example.org/a\nhttps://example.org/a\n")
            args = argparse.Namespace(url=[], urls_file=file, allow_domain=["example.org"], max_urls=25)
            self.assertEqual(list_urls(args), ["https://example.org/a"])


class ApiTests(unittest.TestCase):
    def test_only_local_api(self):
        with self.assertRaises(ValueError):
            WebUI("https://example.org", "token", "kb")
        with self.assertRaises(ValueError):
            WebUI("http://127.0.0.1:8080", "token", "kb")

    @patch("ingest.webui.requests.Session")
    def test_upload_poll_and_link(self, session_cls):
        session = session_cls.return_value
        responses = []
        for data in ({"id": "file123"}, {"status": "completed"}, {"id": "kb"}):
            response = MagicMock()
            response.status_code = 200
            response.json.return_value = data
            responses.append(response)
        session.request.side_effect = responses
        client = WebUI("http://127.0.0.1:3000", "token", "kb")
        file_id = client.upload("page.md", "# title\nbody")
        client.wait_indexed(file_id, 10)
        client.add_to_knowledge(file_id)
        paths = [call.args[1] for call in session.request.call_args_list]
        self.assertEqual(paths, [
            "http://127.0.0.1:3000/api/v1/files/",
            "http://127.0.0.1:3000/api/v1/files/file123/process/status",
            "http://127.0.0.1:3000/api/v1/knowledge/kb/file/add",
        ])
        self.assertFalse(session.trust_env)


if __name__ == "__main__":
    unittest.main()
