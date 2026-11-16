"""Discovery limits must bound work without changing supported source ordering."""

from collections import deque
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import MagicMock, patch

from ingest.documents import DocumentError
from ingest.folder import MAX_DISCOVERED_ENTRIES, discover_import_folder
from ingest.sitemap import sitemap_urls


class FolderDiscoveryTests(unittest.TestCase):
    def test_stops_reading_tree_at_entry_limit(self):
        consumed = []

        def entries():
            for n in range(MAX_DISCOVERED_ENTRIES + 1):
                consumed.append(n)
                yield Path(f"ignored-{n}.txt")
            self.fail("Discovery traversed beyond the first excessive entry")

        with TemporaryDirectory() as temp:
            with patch.object(Path, "rglob", return_value=entries()):
                with self.assertRaisesRegex(
                    DocumentError, "Import folder contains too many entries"
                ):
                    discover_import_folder(Path(temp))
        self.assertEqual(len(consumed), MAX_DISCOVERED_ENTRIES + 1)

    def test_exact_entry_limit_is_accepted_and_sorted(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            paths = [root / "z.pdf", root / "a.pdf"]
            for path in paths:
                path.write_bytes(b"placeholder")
            with patch("ingest.folder.MAX_DISCOVERED_ENTRIES", 2):
                with patch.object(Path, "rglob", return_value=iter(paths)):
                    self.assertEqual(
                        discover_import_folder(root), ([paths[1], paths[0]], [], [])
                    )


class SitemapQueueTests(unittest.TestCase):
    def test_duplicates_and_cycles_are_not_enqueued(self):
        queues = []

        class TrackedQueue(deque):
            def __init__(self, values=()):
                super().__init__(values)
                self.enqueued = list(self)
                queues.append(self)

            def append(self, value):
                self.enqueued.append(value)
                super().append(value)

        base = "https://example.org/"
        fetcher = MagicMock(domains={"example.org"})
        locations = [
            base + "root.xml",
            base + "b.xml",
            base + "b.xml",
            base + "c.xml",
        ] * 100
        index = (
            "<sitemapindex>"
            + "".join(f"<sitemap><loc>{url}</loc></sitemap>" for url in locations)
            + "</sitemapindex>"
        )
        fetcher.get_resource.side_effect = [
            index.encode(),
            b"<urlset><url><loc>https://example.org/z</loc></url></urlset>",
            b"<urlset><url><loc>https://example.org/a</loc></url></urlset>",
        ]
        with patch("ingest.sitemap.deque", TrackedQueue):
            result = sitemap_urls(fetcher, [base + "root.xml"] * 100)
        self.assertEqual(result, [base + "a", base + "z"])
        self.assertEqual(
            queues[0].enqueued, [base + "root.xml", base + "b.xml", base + "c.xml"]
        )
        self.assertEqual(
            [call.args[0] for call in fetcher.get_resource.call_args_list],
            queues[0].enqueued,
        )

    def test_unique_map_budget_and_first_discovery_order_are_preserved(self):
        base = "https://example.org/"
        fetcher = MagicMock(domains={"example.org"})
        fetcher.get_resource.side_effect = [
            b"<sitemapindex><sitemap><loc>https://example.org/b.xml</loc></sitemap><sitemap><loc>https://example.org/c.xml</loc></sitemap></sitemapindex>",
            b"<urlset><url><loc>https://example.org/b</loc></url></urlset>",
        ]
        self.assertEqual(
            sitemap_urls(fetcher, [base + "root.xml", base + "root.xml"], max_maps=2),
            [base + "b"],
        )
        self.assertEqual(
            [call.args[0] for call in fetcher.get_resource.call_args_list],
            [base + "root.xml", base + "b.xml"],
        )
