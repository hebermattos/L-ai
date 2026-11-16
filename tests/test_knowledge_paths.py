"""Keep English-facing paths and safe upgrades covered by tests."""
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from ingest.cli import parse_args, format_doc

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/migrate-knowledge.sh"


class KnowledgePathTests(unittest.TestCase):
    def test_default_state_uses_english_directory(self):
        self.assertEqual(parse_args([]).state, Path("knowledge/.web-ingest.sqlite3"))

    def test_formatted_web_document_uses_english_metadata(self):
        result = format_doc("https://example.org/page", "Title", "Body")
        self.assertIn("Original source:", result)
        self.assertIn("Collected on:", result)

    @unittest.skipUnless(os.name == "posix", "Migration script requires a POSIX Bash environment")
    def test_migration_does_not_overwrite_existing_destination(self):
        # Test the migration script in an isolated copied directory layout.
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "scripts").mkdir()
            (root / "scripts/migrate-knowledge.sh").write_bytes(SCRIPT.read_bytes())
            (root / "biblioteca").mkdir()
            (root / "biblioteca/.web-ingest.sqlite3").write_text("legacy", encoding="utf-8")
            (root / "knowledge").mkdir()
            (root / "knowledge/.web-ingest.sqlite3").write_text("new", encoding="utf-8")
            run = subprocess.run(["bash", str(root / "scripts/migrate-knowledge.sh")],
                                 capture_output=True, text=True, check=False)
            self.assertNotEqual(run.returncode, 0)
            self.assertEqual((root / "biblioteca/.web-ingest.sqlite3").read_text(), "legacy")
            self.assertEqual((root / "knowledge/.web-ingest.sqlite3").read_text(), "new")

    @unittest.skipUnless(os.name == "posix", "Migration script requires a POSIX Bash environment")
    def test_migration_preserves_existing_state(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "scripts").mkdir()
            (root / "scripts/migrate-knowledge.sh").write_bytes(SCRIPT.read_bytes())
            (root / "biblioteca").mkdir()
            (root / "biblioteca/.web-ingest.sqlite3").write_text("legacy", encoding="utf-8")
            run = subprocess.run(["bash", str(root / "scripts/migrate-knowledge.sh")],
                                 capture_output=True, text=True, check=False)
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertEqual((root / "knowledge/.web-ingest.sqlite3").read_text(), "legacy")
            self.assertFalse((root / "biblioteca").exists())


if __name__ == "__main__":
    unittest.main()
