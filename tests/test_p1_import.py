"""P1 crawler, local PDF/EPUB and command-line compatibility."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from ingest.cli import list_urls, run
from ingest.crawler import crawl, discover_links
from ingest.documents import DocumentError, file_paths, format_document, read_document

HTML = b"""<html><body><a href="/library/b">Book B</a>
<a href="https://evil.example/item">outside</a>
<a href="/other/page">outside prefix</a>
<a href="/library/a#section">duplicate</a>
<a rel="nofollow" href="/library/c">no follow</a>
<a href="/library/file.pdf">PDF</a></body></html>"""


class CrawlTests(unittest.TestCase):
    def test_link_scoping_and_dedup(self):
        found = discover_links(HTML, "https://example.org/library/a",
                               {"example.org"}, "/library/")
        self.assertEqual(found, ["https://example.org/library/b",
                                 "https://example.org/library/a"])

    def test_bounded_crawl_and_depth(self):
        fetcher = MagicMock(domains={"example.org"})
        fetcher.get.return_value = HTML
        pages = list(crawl(fetcher, ["https://example.org/library/a"], max_pages=2, max_depth=1))
        self.assertEqual([page[0] for page in pages],
                         ["https://example.org/library/a", "https://example.org/library/b"])
        self.assertEqual(fetcher.get.call_count, 2)

    def test_no_recursive_discovery_at_depth_zero(self):
        fetcher = MagicMock(domains={"example.org"})
        fetcher.get.return_value = HTML
        pages = list(crawl(fetcher, ["https://example.org/library/a"], max_pages=25, max_depth=0))
        self.assertEqual(len(pages), 1)

    def test_invalid_crawler_limits(self):
        fetcher = MagicMock(domains={"example.org"})
        with self.assertRaises(ValueError):
            list(crawl(fetcher, ["https://example.org/"], max_pages=101))


class DocumentTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_real_pdf(self):
        import fitz
        path = self.root / "sample.pdf"
        pdf = fitz.open()
        pdf.set_metadata({"title": "Alchemy", "author": "Researcher"})
        page = pdf.new_page()
        page.insert_text((72,72), ("An account of alchemy and historical symbolism.\\n" * 5))
        pdf.save(path)
        pdf.close()
        doc = read_document(path)
        self.assertEqual(doc.title, "Alchemy")
        self.assertIn("Página 1", doc.body)
        self.assertIn("Researcher", format_document(doc))

    def test_real_epub(self):
        from ebooklib import epub
        path = self.root / "sample.epub"
        book = epub.EpubBook()
        book.set_identifier("book-test")
        book.set_title("Hermetic Texts")
        book.set_language("en")
        book.add_author("Author")
        chapter = epub.EpubHtml(title="Section", file_name="chap1.xhtml", lang="en")
        chapter.content = "<html><body><p>" + ("Historical hermeticism " * 15) + "</p><script>bad()</script></body></html>"
        book.add_item(chapter)
        book.toc = (chapter,)
        book.spine = ["nav", chapter]
        book.add_item(epub.EpubNcx())
        book.add_item(epub.EpubNav())
        epub.write_epub(str(path), book)
        doc = read_document(path)
        self.assertEqual(doc.title, "Hermetic Texts")
        self.assertIn("Historical hermeticism", doc.body)
        self.assertNotIn("bad()", doc.body)

    def test_reject_excessive_epub_ratio(self):
        from zipfile import ZipFile, ZIP_DEFLATED
        path = self.root / "bomb.epub"
        with ZipFile(path, "w", compression=ZIP_DEFLATED) as z:
            z.writestr("huge.xhtml", "A" * 200_000)
        with self.assertRaises(DocumentError):
            read_document(path)

    def test_reject_symlink_and_unsupported_file(self):
        original = self.root / "file.pdf"
        original.write_bytes(b"not a pdf")
        (self.root / "other.txt").write_text("content")
        link = self.root / "link.pdf"
        link.symlink_to(original)
        with self.assertRaises(DocumentError):
            file_paths([link], None)
        with self.assertRaises(DocumentError):
            file_paths([self.root / "other.txt"], None)

    def test_document_directory_limit(self):
        for i in range(3):
            (self.root / f"file-{i}.pdf").write_bytes(b"fake")
        with self.assertRaises(DocumentError):
            file_paths([], self.root, limit=2)

    def test_cli_local_only_dry_run(self):
        path = self.root / "sample.pdf"
        path.write_bytes(b"fake")
        with patch("ingest.cli.read_document") as read:
            read.return_value = MagicMock(source=path.as_uri(), title="Sample",
                                          body="A sample body " * 15, author="")
            self.assertEqual(run(["--file", str(path), "--dry-run"]), 0)
            read.assert_called_once()


if __name__ == "__main__":
    unittest.main()
