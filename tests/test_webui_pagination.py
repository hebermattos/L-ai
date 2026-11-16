"""Open WebUI pagination contracts across supported response shapes."""

import unittest
from unittest.mock import MagicMock

from ingest.webui import WebUI, WebUIError


class PaginationTests(unittest.TestCase):
    def setUp(self):
        self.api = WebUI("http://127.0.0.1:3000", "secret", "kb")
        self.addCleanup(self.api.close)
        self.api._request = MagicMock()

    def test_has_more_and_items_find_file_on_second_page(self):
        self.api._request.side_effect = [
            {"items": [{"id": "other"}], "has_more": True},
            {"items": [{"file_id": "target"}], "has_more": False},
        ]
        self.assertTrue(self.api.knowledge_has_file("target"))
        self.assertEqual(
            [call.kwargs["params"] for call in self.api._request.call_args_list],
            [{"page": 1}, {"page": 2}],
        )

    def test_total_continues_without_has_more(self):
        self.api._request.side_effect = [
            {"files": [{"id": "other"}], "total": 2},
            {"files": [{"id": "target"}], "total": 2},
        ]
        self.assertTrue(self.api.knowledge_has_file("target"))
        self.assertEqual(self.api._request.call_count, 2)

    def test_array_shape_continues_full_pages_and_stops_at_short_page(self):
        self.api._request.side_effect = [
            [{"id": str(n)} for n in range(50)],
            [{"id": "last"}],
        ]
        self.assertFalse(self.api.knowledge_has_file("missing"))
        self.assertEqual(self.api._request.call_count, 2)

    def test_array_shape_finds_target_on_next_page(self):
        self.api._request.side_effect = [
            [{"id": str(n)} for n in range(50)],
            [{"id": "target"}],
        ]
        self.assertTrue(self.api.knowledge_has_file("target"))
        self.assertEqual(self.api._request.call_count, 2)

    def test_total_exhausted_or_empty_page_reports_missing(self):
        for data in (
            {"files": [{"id": "other"}], "total": 1},
            {"files": [], "total": 100},
            [],
        ):
            with self.subTest(data=data):
                self.api._request.reset_mock()
                self.api._request.return_value = data
                self.assertFalse(self.api.knowledge_has_file("missing"))
                self.api._request.assert_called_once()

    def test_unending_pagination_hits_limit(self):
        self.api._request.return_value = {"files": [], "has_more": True}
        with self.assertRaisesRegex(WebUIError, "Exceeded Knowledge pagination limit"):
            self.api.knowledge_has_file("missing", max_pages=3)
        self.assertEqual(self.api._request.call_count, 3)

    def test_malformed_payloads_fail_explicitly(self):
        for data, message in (
            (None, "Unexpected Knowledge list response"),
            ("invalid", "Unexpected Knowledge list response"),
            ({"files": None}, "Unexpected Knowledge files payload"),
            ({"items": {}}, "Unexpected Knowledge files payload"),
        ):
            with self.subTest(data=data):
                self.api._request.return_value = data
                with self.assertRaisesRegex(WebUIError, message):
                    self.api.knowledge_has_file("target")

    def test_found_file_stops_before_has_more(self):
        self.api._request.return_value = {"files": [{"id": "target"}], "has_more": True}
        self.assertTrue(self.api.knowledge_has_file("target"))
        self.api._request.assert_called_once()
