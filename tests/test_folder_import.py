"""Tests for single-command document and URL-list ingestion."""

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

from ingest.cli import list_urls, parse_args, run
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
            (root / "nested/more.txt").write_text(
                "https://example.org/b\n", encoding="utf-8")
            docs, urls = discover_import_folder(root)
            self.assertEqual({p.name for p in docs}, {"a.pdf", "b.epub"})
            args = parse_args(["--import-folder", str(root), "--allow-domain", "example.org"])
            self.assertEqual(list_urls(args, urls),
                             ["https://example.org/b", "https://example.org/a"])

    def test_rejects_symlinks(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "urls.txt").symlink_to(root / "missing.txt")
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
