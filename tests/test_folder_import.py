"""Tests for single-command document and URL-list ingestion."""

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from ingest.cli import list_urls, parse_args, prepare_inputs, run
from ingest.documents import DocumentError
from ingest.folder import discover_import_folder


class FolderImportTests(TestCase):
    def test_discovers_nested_documents_and_multiple_url_lists(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "nested").mkdir()
            (root / "a.pdf").write_bytes(b"%PDF-placeholder")
            (root / "nested/b.epub").write_bytes(b"EPUB-placeholder")
            (root / "urls.txt").write_text(
                "# sample\nhttps://example.org/a\nhttps://example.org/a\n",
                encoding="utf-8")
            (root / "nested/urls.txt").write_text(
                "https://example.org/b\n", encoding="utf-8")
            docs, urls, crawl_urls = discover_import_folder(root)
            self.assertEqual(crawl_urls, [])
            self.assertEqual({p.name for p in docs}, {"a.pdf", "b.epub"})
            args = parse_args(["--import-folder", str(root), "--allow-domain", "example.org"])
            self.assertEqual(list_urls(args, urls),
                             ["https://example.org/b", "https://example.org/a"])


    def test_distinct_normal_and_recursive_manifests(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "urls.txt").write_text(
                "https://example.org/direct\n", encoding="utf-8")
            (root / "crawl.txt").write_text(
                "https://example.org/docs/index\n", encoding="utf-8")
            (root / "notes.txt").write_text(
                "This is not a URL manifest", encoding="utf-8")
            documents, direct, recursive = discover_import_folder(root)
            self.assertEqual(documents, [])
            self.assertEqual(direct, ["https://example.org/direct"])
            self.assertEqual(recursive, ["https://example.org/docs/index"])

    @patch("ingest.cli.read_url_lines", return_value=["https://example.org/manual"])
    def test_cli_manifest_is_read_once_for_crawl(self, read_manifest):
        with TemporaryDirectory() as temp:
            manifest = Path(temp) / "manual.txt"
            manifest.touch()
            args = parse_args([
                "--urls-file", str(manifest), "--crawl", "--allow-domain", "example.org",
            ])
            plan = prepare_inputs(args)
        read_manifest.assert_called_once_with(manifest)
        self.assertEqual(plan.urls, ["https://example.org/manual"])
        self.assertEqual(plan.crawl_targets, set(plan.urls))

    @patch("ingest.cli.crawl")
    @patch("ingest.cli.extract_markdown", return_value=("Example", "Some content " * 12))
    @patch("ingest.cli.SafeFetcher")
    def test_mixed_import_crawls_only_crawl_manifest(
            self, fetcher, extract, crawler):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "urls.txt").write_text(
                "https://example.org/direct\n", encoding="utf-8")
            (root / "crawl.txt").write_text(
                "https://example.org/docs/start\n", encoding="utf-8")
            fetcher.return_value.get.return_value = b"<html>Direct page</html>"
            crawler.return_value = iter([
                ("https://example.org/docs/start", b"<html>Crawled page</html>", None)
            ])
            result = run([
                "--import-folder", str(root), "--allow-domain", "example.org",
                "--dry-run", "--max-depth", "2"
            ])
            self.assertEqual(result, 0)
            crawler.assert_called_once_with(
                fetcher.return_value,
                ["https://example.org/docs/start"], 25, 2)
            fetcher.return_value.get.assert_called_once_with(
                "https://example.org/direct")
            self.assertEqual(extract.call_count, 2)

    @patch("ingest.cli.crawl")
    @patch("ingest.cli.extract_markdown", return_value=("Example", "Some content " * 12))
    @patch("ingest.cli.SafeFetcher")
    def test_duplicate_across_manifests_is_only_crawled(
            self, fetcher, extract, crawler):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            url = "https://example.org/shared"
            (root / "urls.txt").write_text(url + "\n", encoding="utf-8")
            (root / "crawl.txt").write_text(url + "\n", encoding="utf-8")
            crawler.return_value = iter([(url, b"<html>Crawled</html>", None)])
            self.assertEqual(run([
                "--import-folder", str(root), "--allow-domain", "example.org",
                "--dry-run"]), 0)
            fetcher.return_value.get.assert_not_called()
            crawler.assert_called_once()
            self.assertEqual(extract.call_count, 1)

    def test_crawl_manifest_must_be_allowlisted(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "crawl.txt").write_text(
                "https://outside.test/docs\n", encoding="utf-8")
            self.assertEqual(run([
                "--import-folder", str(root), "--allow-domain", "example.org",
                "--dry-run"]), 2)

    def test_rejects_symlinks(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            try:
                (root / "urls.txt").symlink_to(root / "missing.txt")
            except OSError as exc:
                if getattr(exc, "winerror", None) == 1314:
                    self.skipTest("Windows runner lacks symbolic-link privileges")
                raise
            with self.assertRaises(DocumentError):
                discover_import_folder(root)

    def test_rejects_oversized_url_manifest(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "urls.txt").write_text("x" * 65537, encoding="utf-8")
            with self.assertRaises(DocumentError):
                discover_import_folder(root)

    def test_requires_allowlisted_domain(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "urls.txt").write_text("https://example.org/a\n", encoding="utf-8")
            self.assertEqual(run(["--import-folder", str(root), "--dry-run"]), 2)

    def test_rejects_http_and_other_unapproved_urls(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "urls.txt").write_text("http://example.org/a\n", encoding="utf-8")
            self.assertEqual(run(["--import-folder", str(root),
                                  "--allow-domain", "example.org", "--dry-run"]), 2)

    @patch("ingest.cli.extract_markdown", return_value=("Example", "Sample content " * 12))
    @patch("ingest.cli.SafeFetcher")
    def test_single_command_dry_run_extracts_web_content(self, fetcher, extract):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "urls.txt").write_text("https://example.org/a\n", encoding="utf-8")
            fetcher.return_value.get.return_value = b"<html>Sample content</html>"
            result = run(["--import-folder", str(root),
                          "--allow-domain", "example.org", "--dry-run"])
            self.assertEqual(result, 0)
            self.assertEqual(extract.call_count, 1)

    def test_empty_folder_is_rejected(self):
        with TemporaryDirectory() as temp:
            self.assertEqual(run(["--import-folder", temp, "--dry-run"]), 2)

    def test_document_count_limit_still_applies(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "a.pdf").write_bytes(b"content")
            (root / "b.epub").write_bytes(b"content")
            self.assertEqual(run(["--import-folder", temp, "--max-documents", "1",
                                  "--dry-run"]), 2)


if __name__ == "__main__":
    import unittest
    unittest.main()
