"""Observable ingestion contracts to preserve during internal refactoring."""

from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime, timezone
import hashlib
import io
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import MagicMock, patch

from ingest.cli import format_doc, list_urls, parse_args, run
from ingest.documents import DocumentError, format_document, read_document
from ingest.folder import discover_import_folder
from ingest.remote import read_remote_pdf
from ingest.service import ingest_page
from ingest.state import IngestState
from ingest.web import SourceRejected


class CLIContracts(unittest.TestCase):
    def capture(self, argv):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = run(argv)
        return code, out.getvalue(), err.getvalue()

    def test_invalid_input_exit_and_message(self):
        code, out, err = self.capture([])
        self.assertEqual(code, 2)
        self.assertEqual(out, "")
        self.assertEqual(
            err,
            "Invalid input: Provide --url, --urls-file, --file, --directory, or --import-folder with supported content\n",
        )

    @patch("ingest.cli.IngestState")
    @patch("ingest.cli.WebUI")
    @patch("ingest.cli.extract_markdown", return_value=("Title", "body" * 30))
    @patch("ingest.cli.SafeFetcher")
    def test_dry_run_output_without_remote_or_state_writes(
        self, fetch, extract, webui, state
    ):
        code, out, err = self.capture(
            [
                "--url",
                "https://example.org/a",
                "--allow-domain",
                "example.org",
                "--dry-run",
            ]
        )
        self.assertEqual(
            (code, out, err),
            (0, "DRY RUN https://example.org/a: Title (120 chars)\n", ""),
        )
        webui.assert_not_called()
        state.assert_not_called()

    @patch("ingest.cli.extract_markdown", return_value=("Title", "body" * 30))
    @patch("ingest.cli.SafeFetcher")
    def test_failed_page_continues_to_next_source(self, fetch, extract):
        fetch.return_value.get.side_effect = [SourceRejected("blocked"), b"html"]
        code, out, err = self.capture(
            [
                "--url",
                "https://example.org/a",
                "--url",
                "https://example.org/b",
                "--allow-domain",
                "example.org",
                "--dry-run",
            ]
        )
        self.assertEqual(code, 1)
        self.assertEqual(err, "FAILED web page: blocked\n")
        self.assertEqual(out, "DRY RUN https://example.org/b: Title (120 chars)\n")

    def test_web_document_format(self):
        date = datetime.now(timezone.utc).date().isoformat()
        self.assertEqual(
            format_doc("https://example.org/a", "Title", "Body"),
            f"# Title\n\nOriginal source: https://example.org/a\nCollected on: {date}\n\nBody\n",
        )

    def test_manifest_comments_order_and_duplicate_limit(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "urls.txt").write_text(
                "  # comment\n\n https://example.org/b \nhttps://example.org/a\nhttps://example.org/b\n",
                encoding="utf-8",
            )
            _, urls, _ = discover_import_folder(root)
            args = parse_args(
                ["--urls-file", str(root / "urls.txt"), "--allow-domain", "example.org"]
            )
            self.assertEqual(
                list_urls(args), ["https://example.org/b", "https://example.org/a"]
            )
            self.assertEqual(
                urls,
                [
                    "https://example.org/b",
                    "https://example.org/a",
                    "https://example.org/b",
                ],
            )
            args.max_urls = 2
            with self.assertRaisesRegex(ValueError, "URL count outside allowed range"):
                list_urls(args)


class PDFContracts(unittest.TestCase):
    def make_pdf(self, path, *, text=True, metadata=True):
        import fitz

        with fitz.open() as pdf:
            if metadata:
                pdf.set_metadata({"title": "Technical Notes", "author": "Researcher"})
            page = pdf.new_page()
            if text:
                page.insert_text((72, 72), "Software design and architecture.\n" * 8)
            pdf.new_page()  # Empty pages must not produce section headings.
            pdf.save(path)

    def test_local_remote_pdf_text_and_format(self):
        with TemporaryDirectory() as temp:
            path = Path(temp) / "sample.pdf"
            self.make_pdf(path)
            fetcher = MagicMock(domains={"example.org"})
            fetcher.get_resource.return_value = path.read_bytes()
            local = read_document(path)
            remote = read_remote_pdf(fetcher, "https://example.org/sample.pdf")
            self.assertEqual(
                (local.title, local.author, local.body),
                (remote.title, remote.author, remote.body),
            )
            self.assertTrue(local.body.startswith("## Page 1\n\nSoftware"))
            self.assertNotIn("Page 2", local.body)
            self.assertEqual(
                format_document(local),
                f"# Technical Notes\n\nAuthor: Researcher\nFormat: pdf\n\n{local.body}\n",
            )
            self.assertEqual(
                format_document(remote),
                f"# Technical Notes\n\nOriginal source: https://example.org/sample.pdf\nAuthor: Researcher\nFormat: pdf\n\n{remote.body}\n",
            )

    def test_pdf_title_fallbacks_remain_distinct(self):
        with TemporaryDirectory() as temp:
            path = Path(temp) / "sample.pdf"
            self.make_pdf(path, metadata=False)
            fetcher = MagicMock(domains={"example.org"})
            fetcher.get_resource.return_value = path.read_bytes()
            self.assertEqual(read_document(path).title, "sample")
            self.assertEqual(
                read_remote_pdf(fetcher, "https://example.org/sample.pdf").title,
                "sample.pdf",
            )

    def test_empty_pdf_error_contracts(self):
        with TemporaryDirectory() as temp:
            path = Path(temp) / "sample.pdf"
            self.make_pdf(path, text=False)
            fetcher = MagicMock(domains={"example.org"})
            fetcher.get_resource.return_value = path.read_bytes()
            with self.assertRaisesRegex(
                DocumentError,
                "No substantial text; scanned PDFs require the --ocr option",
            ):
                read_document(path)
            with self.assertRaisesRegex(DocumentError, "Invalid remote PDF") as caught:
                read_remote_pdf(fetcher, "https://example.org/sample.pdf")
            self.assertIn(
                "PDF without selectable text", str(caught.exception.__cause__)
            )


class StateContracts(unittest.TestCase):
    def test_hash_filename_result_and_schema(self):
        with TemporaryDirectory() as temp:
            path = Path(temp) / "state.sqlite3"
            state = IngestState(path)
            self.addCleanup(state.close)
            api = MagicMock(knowledge_id="kb")
            api.upload.return_value = "file-id"
            url, body, document = "https://example.org/a", "body", "# Title\nbody"
            self.assertEqual(
                ingest_page(state, api, url, "Title", body, document), "IMPORTED"
            )
            filename = hashlib.sha256(url.encode("utf-8")).hexdigest()[:20] + ".md"
            api.upload.assert_called_once_with(filename, document)
            digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
            self.assertEqual(
                state.get(url, "kb"),
                {"hash": digest, "file_id": "file-id", "status": "ready"},
            )
            with sqlite3.connect(path) as db:
                self.assertEqual(
                    [r[1] for r in db.execute("PRAGMA table_info(pages)")],
                    ["url", "knowledge_id", "hash", "file_id", "status"],
                )
            self.assertEqual(
                ingest_page(state, api, url, "Title", body, document), "UNCHANGED"
            )
            self.assertEqual(
                ingest_page(state, api, url + "/copy", "Title", body, document),
                "DUPLICATE CONTENT",
            )
