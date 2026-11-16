import unittest
from unittest.mock import patch
from ingest.cli import parse_args, run

class PipelineCliTests(unittest.TestCase):
    def test_cli_flags(self):
        args = parse_args(["--sitemap", "https://example.org/sitemap.xml", "--remote-pdf",
                           "https://example.org/book.pdf", "--allow-domain", "example.org", "--ocr"])
        self.assertTrue(args.ocr)
        self.assertEqual(len(args.sitemap), 1)

    def test_requires_authorization_for_sitemap(self):
        self.assertEqual(run(["--sitemap", "https://example.org/sitemap.xml", "--dry-run"]), 2)

    @patch("ingest.cli.sitemap_urls")
    @patch("ingest.cli.SafeFetcher")
    @patch("ingest.cli.extract_markdown")
    def test_sitemap_to_extraction(self, extract, factory, sitemap):
        sitemap.return_value = ["https://example.org/a"]
        extract.return_value = ("Page", "Sample historical paragraph " * 8)
        factory.return_value.get.return_value = b"<html>text</html>"
        result = run(["--sitemap", "https://example.org/sitemap.xml",
                      "--allow-domain", "example.org", "--dry-run"])
        self.assertEqual(result, 0)
        self.assertEqual(extract.call_count, 1)
