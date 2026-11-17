"""Knowledge management, explicit selection, and base isolation contracts."""
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from ingest import cli, knowledge
from ingest.service import ingest_page
from ingest.state import IngestState
from ingest.webui import WebUI, WebUIError


class KnowledgeApiTests(unittest.TestCase):
    def setUp(self):
        self.api = WebUI("http://127.0.0.1:3000", "secret")
        self.addCleanup(self.api.close)
        self.api._request = MagicMock()

    def test_paginated_catalog_and_name_resolution(self):
        self.api._request.side_effect = [
            {"items": [{"id": "a", "name": "Programming"}], "total": 2},
            {"items": [{"id": "b", "name": "Security"}], "total": 2},
        ]
        self.assertEqual(self.api.resolve_knowledge("Security"), "b")
        self.assertEqual(self.api._request.call_args.kwargs["params"], {"page": 2})

    def test_legacy_array_catalog(self):
        self.api._request.return_value = [{"id": "a", "name": "Programming"}]
        self.assertEqual(self.api.resolve_knowledge("Programming"), "a")
        self.api._request.assert_called_once()

    def test_missing_and_ambiguous_names_fail(self):
        for items, message in [
            ([], "not found"),
            ([{"id": "a", "name": "Same"}, {"id": "b", "name": "Same"}], "Ambiguous"),
        ]:
            with self.subTest(items=items):
                self.api._request.return_value = items
                with self.assertRaisesRegex(WebUIError, message):
                    self.api.resolve_knowledge("Same")

    def test_invalid_or_incomplete_catalogs_fail(self):
        for payload in [None, {}, {"items": None, "total": 1},
                        {"items": [], "total": "2"}, {"items": [], "total": 1},
                        [{"id": "../bad", "name": "Bad"}], [{"id": "a"}]]:
            with self.subTest(payload=payload):
                self.api._request.return_value = payload
                with self.assertRaises(WebUIError):
                    self.api.list_knowledge()

    def test_catalog_pagination_is_bounded(self):
        self.api._request.side_effect = [
            {"items": [{"id": "a", "name": "A"}], "total": 3},
            {"items": [{"id": "b", "name": "B"}], "total": 3},
        ]
        with self.assertRaisesRegex(WebUIError, "pagination limit"):
            self.api.list_knowledge(max_pages=2)

    def test_create_sends_name_description_and_no_sharing_grants(self):
        self.api._request.return_value = {"id": "new-id", "name": "Programming"}
        self.assertEqual(self.api.create_knowledge(" Programming ", "Manuals")["id"], "new-id")
        self.api._request.assert_called_once_with(
            "POST", "/api/v1/knowledge/create",
            json={"name": "Programming", "description": "Manuals"})

    def test_blank_create_name_does_not_send_request(self):
        with self.assertRaises(ValueError):
            self.api.create_knowledge("  ")
        self.api._request.assert_not_called()

    def test_invalid_create_response_is_reported(self):
        self.api._request.return_value = None
        with self.assertRaises(WebUIError):
            self.api.create_knowledge("Programming")


class KnowledgeCommandTests(unittest.TestCase):
    @patch.dict(os.environ, {"OPEN_WEBUI_API_KEY": "secret"}, clear=True)
    @patch("ingest.knowledge.WebUI")
    def test_list_and_create_output_json(self, factory):
        api = factory.return_value.__enter__.return_value
        api.list_knowledge.return_value = [{"id": "a", "name": "Programming"}]
        api.create_knowledge.return_value = {"id": "b", "name": "Security"}
        for args, expected in [
            (["list"], [{"id": "a", "name": "Programming"}]),
            (["create", "--name", "Security", "--description", "Manuals"],
             {"id": "b", "name": "Security"}),
        ]:
            with self.subTest(args=args), patch("sys.stdout", new_callable=io.StringIO) as output:
                self.assertEqual(knowledge.run(args), 0)
                self.assertEqual(json.loads(output.getvalue()), expected)
        api.create_knowledge.assert_called_once_with("Security", "Manuals")

    @patch.dict(os.environ, {}, clear=True)
    def test_missing_credentials_fail_cleanly(self):
        with patch("sys.stderr", new_callable=io.StringIO) as output:
            self.assertEqual(knowledge.run(["list"]), 2)
        self.assertNotIn("Traceback", output.getvalue())

    @patch.dict(os.environ, {"OPEN_WEBUI_API_KEY": "secret"}, clear=True)
    @patch("ingest.knowledge.WebUI")
    def test_api_failure_is_nonzero(self, factory):
        factory.return_value.__enter__.return_value.list_knowledge.side_effect = WebUIError("HTTP 403")
        self.assertEqual(knowledge.run(["list"]), 2)


class KnowledgeSelectionTests(unittest.TestCase):
    @patch.dict(os.environ, {"OPEN_WEBUI_KNOWLEDGE_ID": "env-id"}, clear=True)
    def test_explicit_selectors_override_environment(self):
        self.assertEqual(cli.parse_args([]).knowledge_id, "env-id")
        self.assertEqual(cli.parse_args(["--knowledge-id", "other"]).knowledge_id, "other")
        args = cli.parse_args(["--knowledge-name", "Security"])
        self.assertIsNone(args.knowledge_id)
        self.assertEqual(args.knowledge_name, "Security")
        with self.assertRaises(SystemExit):
            cli.parse_args(["--knowledge-id", "a", "--knowledge-name", "B"])

    @patch.dict(os.environ, {"OPEN_WEBUI_API_KEY": "secret", "OPEN_WEBUI_KNOWLEDGE_ID": "env-id"})
    @patch("ingest.cli.execute_sources", return_value=0)
    @patch("ingest.cli.IngestState")
    @patch("ingest.cli.WebUI")
    @patch("ingest.cli.prepare_inputs", return_value=cli.IngestPlan([], set(), []))
    def test_name_resolved_before_state_or_upload(self, prepare, factory, state, execute):
        api = factory.return_value
        api.resolve_knowledge.return_value = "selected-id"
        self.assertEqual(cli.run(["--knowledge-name", "Security"]), 0)
        self.assertEqual(api.knowledge_id, "selected-id")
        api.resolve_knowledge.assert_called_once_with("Security")
        self.assertIs(execute.call_args.args[3], api)
        api.close.assert_called_once()

    @patch.dict(os.environ, {"OPEN_WEBUI_API_KEY": "secret"}, clear=True)
    @patch("ingest.cli.IngestState")
    @patch("ingest.cli.WebUI")
    @patch("ingest.cli.prepare_inputs", return_value=cli.IngestPlan([], set(), []))
    def test_failed_resolution_does_not_open_state(self, prepare, factory, state):
        factory.return_value.resolve_knowledge.side_effect = WebUIError("Ambiguous name")
        self.assertEqual(cli.run(["--knowledge-name", "Same"]), 2)
        state.assert_not_called()
        factory.return_value.upload.assert_not_called()
        factory.return_value.close.assert_called_once()

    @patch.dict(os.environ, {}, clear=True)
    @patch("ingest.cli.WebUI")
    @patch("ingest.cli.prepare_inputs", return_value=cli.IngestPlan([], set(), []))
    def test_dry_run_name_requires_no_credentials_or_api(self, prepare, factory):
        self.assertEqual(cli.run(["--knowledge-name", "Security", "--dry-run"]), 0)
        factory.assert_not_called()

    def test_same_source_can_be_imported_and_updated_in_separate_bases(self):
        with tempfile.TemporaryDirectory() as directory, IngestState(Path(directory) / "state.db") as state:
            a, b = MagicMock(), MagicMock()
            a.knowledge_id, b.knowledge_id = "base-a", "base-b"
            a.upload.return_value, b.upload.return_value = "file-a", "file-b"
            for api in (a, b):
                self.assertEqual(ingest_page(state, api, "source", "Title", "body", "doc"), "IMPORTED")
            self.assertEqual(ingest_page(state, a, "source", "Title", "changed", "new doc"), "UPDATED")
            a.update_content.assert_called_once_with("file-a", "new doc")
            b.update_content.assert_not_called()
            self.assertEqual(state.get("source", "base-b")["file_id"], "file-b")
