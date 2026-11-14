"""Unit tests for durable ingestion and mocked Open WebUI API contracts."""
import pathlib
import sqlite3
import tempfile
import unittest
from unittest.mock import MagicMock

from ingest.state import IngestState
from ingest.service import ingest_page
from ingest.webui import WebUI, WebUIError

URL = "https://example.org/book"
BODY = "A passage about hermeticism. " * 8
DOC = "# Book\n\n" + BODY

class StateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = pathlib.Path(self.tmp.name) / "ingest.sqlite3"

    def test_migrate_legacy_schema_and_isolate_kbs(self):
        db = sqlite3.connect(self.path)
        db.execute("CREATE TABLE pages(url TEXT PRIMARY KEY,hash TEXT NOT NULL,file_id TEXT NOT NULL,knowledge_id TEXT NOT NULL)")
        db.execute("INSERT INTO pages VALUES (?,?,?,?)", (URL,"h","id-a","kb-a"))
        db.commit()
        db.close()
        state = IngestState(self.path)
        self.addCleanup(state.close)
        self.assertEqual(state.get(URL,"kb-a")["status"],"ready")
        state.save(URL,"kb-b","h","id-b","ready")
        self.assertEqual(state.get(URL,"kb-a")["file_id"],"id-a")
        self.assertEqual(state.get(URL,"kb-b")["file_id"],"id-b")
        state.migrate()

    def test_duplicate_scoped_to_knowledge(self):
        state = IngestState(self.path)
        self.addCleanup(state.close)
        state.save(URL,"kb-a","h","f","ready")
        self.assertTrue(state.duplicate("h","kb-a",except_url="different"))
        self.assertFalse(state.duplicate("h","kb-b",except_url="different"))

class IngestWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.state = IngestState(pathlib.Path(self.tmp.name)/"state.sqlite3")
        self.addCleanup(self.state.close)
        self.api = MagicMock(knowledge_id="kb-a")
        self.api.upload.return_value = "file-a"
        self.api.knowledge_has_file.return_value = True

    def ingest(self,body=BODY,doc=DOC):
        return ingest_page(self.state,self.api,URL,"Book",body,doc)

    def test_idempotence_and_separate_kb(self):
        self.assertEqual(self.ingest(),"IMPORTED")
        self.assertEqual(self.ingest(),"UNCHANGED")
        self.api.upload.assert_called_once()
        self.api.knowledge_id = "kb-b"
        self.assertEqual(self.ingest(),"IMPORTED")
        self.assertEqual(self.api.upload.call_count,2)

    def test_resume_after_processing_timeout(self):
        self.api.wait_indexed.side_effect = WebUIError("timeout")
        with self.assertRaises(WebUIError):
            self.ingest()
        self.assertEqual(self.state.get(URL,"kb-a")["status"],"uploaded")
        self.api.wait_indexed.side_effect = None
        self.assertEqual(self.ingest(),"RECOVERED")
        self.api.upload.assert_called_once()

    def test_retry_update_after_reindex_error(self):
        self.ingest()
        self.api.update_content.side_effect = WebUIError("indexing failed")
        with self.assertRaises(WebUIError):
            self.ingest("new content","# Changed")
        self.assertEqual(self.state.get(URL,"kb-a")["status"],"updating")
        self.api.update_content.side_effect = None
        self.assertEqual(self.ingest("new content","# Changed"),"UPDATED")
        self.assertEqual(self.state.get(URL,"kb-a")["status"],"ready")

    def test_relink_removed_file(self):
        self.ingest()
        self.api.knowledge_has_file.return_value = False
        self.assertEqual(self.ingest(),"RECOVERED")
        self.assertEqual(self.api.ensure_linked.call_count,2)

class APITests(unittest.TestCase):
    def setUp(self):
        self.api = WebUI("http://127.0.0.1:3000","secret","kb")
        self.api._request = MagicMock()

    def test_no_duplicate_add_for_existing_file(self):
        self.api._request.return_value = {"files":[{"id":"f"}],"total":1}
        self.api.ensure_linked("f")
        self.assertEqual(self.api._request.call_count,1)

    def test_no_success_without_membership(self):
        self.api._request.side_effect = [{"files":[]},{"ok":True},{"files":[]}]
        with self.assertRaises(WebUIError):
            self.api.ensure_linked("f")

    def test_content_update_and_readback(self):
        self.api._request.side_effect = [{},{"content":"new"},{"files":[{"id":"f"}]}]
        self.api.update_content("f","new")
        self.assertIn("/data/content/update",self.api._request.call_args_list[0].args[1])

    def test_reject_mismatched_remote_content(self):
        self.api._request.side_effect = [{},{"content":"old"}]
        with self.assertRaises(WebUIError):
            self.api.update_content("f","new")

    def test_loopback_only(self):
        for url in ["http://evil.example","http://localhost:3000/path","https://localhost:3000"]:
            with self.subTest(url=url),self.assertRaises(ValueError):
                WebUI(url,"secret","kb")
