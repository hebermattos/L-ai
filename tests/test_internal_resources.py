"""Resource cleanup, bounded PDF extraction and deterministic network timing."""

from contextlib import redirect_stderr, redirect_stdout
import io
import os
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import MagicMock, patch

from ingest.cli import run
from ingest.documents import DocumentError, extract_pdf_body
from ingest.state import IngestState
from ingest.web import SafeFetcher
from ingest.webui import WebUI, WebUIError


class ResourceTests(unittest.TestCase):
    @patch("ingest.state.sqlite3.connect")
    @patch(
        "ingest.state.IngestState.migrate", side_effect=RuntimeError("migration failed")
    )
    def test_sqlite_closes_when_initialization_fails(self, migrate, connect):
        with TemporaryDirectory() as temp:
            with self.assertRaisesRegex(RuntimeError, "migration failed"):
                IngestState(Path(temp) / "state.sqlite3")
        connect.return_value.close.assert_called_once_with()

    def test_sqlite_context_closes_on_error_and_keeps_committed_state(self):
        with TemporaryDirectory() as temp:
            path = Path(temp) / "state.sqlite3"
            with self.assertRaisesRegex(RuntimeError, "stop"):
                with IngestState(path) as state:
                    state.save("source", "kb", "hash", "file", "ready")
                    raise RuntimeError("stop")
            with self.assertRaises(sqlite3.ProgrammingError):
                state.db.execute("SELECT 1")
            with IngestState(path) as reopened:
                self.assertEqual(reopened.get("source", "kb")["file_id"], "file")

    @patch("ingest.webui.requests.Session")
    def test_http_session_closes_on_error(self, session):
        with self.assertRaises(RuntimeError):
            with WebUI("http://127.0.0.1:3000", "secret", "kb"):
                raise RuntimeError("stop")
        session.return_value.close.assert_called_once_with()

    @patch.dict(os.environ, {"OPEN_WEBUI_API_KEY": "secret"})
    @patch("ingest.cli.SafeFetcher")
    @patch("ingest.cli.IngestState")
    @patch("ingest.cli.WebUI")
    @patch("ingest.cli.execute_sources")
    def test_cli_closes_both_resources_for_success_and_unexpected_error(
        self, execute, webui, state, fetch
    ):
        args = [
            "--url",
            "https://example.org/a",
            "--allow-domain",
            "example.org",
            "--knowledge-id",
            "kb",
        ]
        execute.return_value = 0
        with redirect_stdout(io.StringIO()):
            self.assertEqual(run(args), 0)
            execute.side_effect = RuntimeError("unexpected")
            with self.assertRaisesRegex(RuntimeError, "unexpected"):
                run(args)
        self.assertEqual(state.return_value.close.call_count, 2)
        self.assertEqual(webui.return_value.close.call_count, 2)

    @patch.dict(os.environ, {"OPEN_WEBUI_API_KEY": "secret"})
    @patch("ingest.cli.SafeFetcher")
    @patch("ingest.cli.IngestState", side_effect=OSError("database unavailable"))
    @patch("ingest.cli.WebUI")
    def test_cli_closes_http_session_if_state_initialization_fails(
        self, webui, state, fetch
    ):
        with self.assertRaises(OSError):
            run(
                [
                    "--url",
                    "https://example.org/a",
                    "--allow-domain",
                    "example.org",
                    "--knowledge-id",
                    "kb",
                ]
            )
        webui.return_value.close.assert_called_once_with()


class TimingTests(unittest.TestCase):
    @patch("ingest.web.public_addresses", return_value=["8.8.8.8"])
    @patch("ingest.web.urllib3.HTTPSConnectionPool")
    def test_fetch_pause_uses_injected_clock(self, pool, dns):
        response = pool.return_value.urlopen.return_value
        response.status = 200
        response.headers = {"Content-Type": "text/html"}
        response.read.return_value = b"html"
        sleep = MagicMock()
        fetcher = SafeFetcher(
            {"example.org"}, clock=MagicMock(side_effect=[1.0, 2.0]), sleep=sleep
        )
        self.assertEqual(fetcher._fetch("https://example.org/a"), (200, b"html"))
        sleep.assert_called_once_with(1.0)
        response.release_conn.assert_called_once_with()
        pool.return_value.close.assert_called_once_with()

    def test_polling_completion_and_timeout_without_real_sleep(self):
        for completed in (True, False):
            with self.subTest(completed=completed):
                current = [0.0]
                delays = []

                def sleep(seconds):
                    delays.append(seconds)
                    current[0] += seconds

                with WebUI(
                    "http://localhost:3000",
                    "secret",
                    "kb",
                    clock=lambda: current[0],
                    sleep=sleep,
                ) as api:
                    api._request = MagicMock(
                        side_effect=[
                            {"status": "pending"},
                            {"status": "completed" if completed else "pending"},
                        ]
                    )
                    if completed:
                        api.wait_indexed("file", seconds=3)
                        self.assertEqual(delays, [2])
                    else:
                        with self.assertRaisesRegex(
                            WebUIError, "Timed out waiting for file processing"
                        ):
                            api.wait_indexed("file", seconds=3)
                        self.assertEqual(delays, [2, 2])
                    self.assertEqual(api._request.call_count, 2)


class PDFExtractionTests(unittest.TestCase):
    def test_corrupt_local_pdf_does_not_stop_batch(self):
        import pymupdf

        with TemporaryDirectory() as temp:
            corrupt = Path(temp) / "corrupt.pdf"
            valid = Path(temp) / "valid.pdf"
            corrupt.write_bytes(b"invalid PDF")
            with pymupdf.open() as doc:
                doc.new_page().insert_textbox(
                    pymupdf.Rect(30, 30, 500, 500), "Readable text. " * 20
                )
                doc.save(valid)
            out, err = io.StringIO(), io.StringIO()
            with redirect_stdout(out), redirect_stderr(err):
                result = run(["--dry-run", "--file", str(corrupt), "--file", str(valid)])
            self.assertEqual(result, 1)
            self.assertIn("FAILED corrupt.pdf: Unable to read PDF", err.getvalue())
            self.assertIn(f"DRY RUN {valid.resolve().as_uri()}", out.getvalue())

    @patch("ingest.documents.MAX_TEXT_CHARS", 5)
    def test_shared_text_limit_retains_source_specific_error(self):
        page = MagicMock()
        page.get_text.return_value = "123456"
        for message in ("PDF extracted text is too large", "Extracted text too large"):
            with (
                self.subTest(message=message),
                self.assertRaisesRegex(DocumentError, message),
            ):
                extract_pdf_body([page], text_limit_error=message)

    @patch("ingest.documents.subprocess.run")
    def test_ocr_is_only_used_for_empty_pages_when_enabled(self, tesseract):
        selectable, scanned = MagicMock(), MagicMock()
        selectable.get_text.return_value = "Selectable text"
        scanned.get_text.return_value = ""
        scanned.get_pixmap.return_value.samples = b"pixels"
        scanned.get_pixmap.return_value.tobytes.return_value = b"png"
        tesseract.return_value.stdout = b" OCR text \n"
        self.assertEqual(
            extract_pdf_body([selectable, scanned]), "## Page 1\n\nSelectable text"
        )
        tesseract.assert_not_called()
        self.assertEqual(
            extract_pdf_body([selectable, scanned], ocr=True),
            "## Page 1\n\nSelectable text\n\n## Page 2\n\nOCR text",
        )
        tesseract.assert_called_once_with(
            ["tesseract", "stdin", "stdout", "-l", "por+eng"],
            input=b"png",
            capture_output=True,
            timeout=45,
            check=True,
        )
        selectable.get_pixmap.assert_not_called()
