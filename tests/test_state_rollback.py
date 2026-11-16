"""Real SQLite migration failures must roll back DDL and preserve legacy data."""

from contextlib import closing
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from ingest.state import IngestState


class MigrationRollbackTests(unittest.TestCase):
    def create_legacy(self, path):
        with closing(sqlite3.connect(path)) as db, db:
            db.execute(
                "CREATE TABLE pages(url TEXT PRIMARY KEY,hash TEXT NOT NULL,file_id TEXT,knowledge_id TEXT NOT NULL)"
            )
            db.executemany(
                "INSERT INTO pages VALUES (?,?,?,?)",
                [
                    ("https://example.org/a", "hash-a", "file-a", "kb-a"),
                    ("https://example.org/b", "hash-b", "file-b", "kb-b"),
                ],
            )

    def snapshot(self, path):
        with closing(sqlite3.connect(path)) as db, db:
            schema = db.execute(
                "SELECT name, type, sql FROM sqlite_master ORDER BY name"
            ).fetchall()
            rows = db.execute("SELECT * FROM pages ORDER BY url").fetchall()
            self.assertEqual(db.execute("PRAGMA integrity_check").fetchone(), ("ok",))
        return schema, rows

    def test_rolls_back_every_intermediate_step_and_can_retry(self):
        stages = (
            "ALTER TABLE pages RENAME",
            "CREATE TABLE pages(",
            "INSERT INTO pages(url",
            "DROP TABLE pages_legacy",
            "CREATE INDEX IF NOT EXISTS pages_hash_idx",
        )
        real_connect = sqlite3.connect
        for stage in stages:
            with self.subTest(stage=stage), TemporaryDirectory() as temp:
                path = Path(temp) / "state.sqlite3"
                self.create_legacy(path)
                original = self.snapshot(path)

                class FailingConnection(sqlite3.Connection):
                    def execute(self, sql, parameters=()):
                        cursor = super().execute(sql, parameters)
                        if stage in sql:
                            raise sqlite3.OperationalError("injected migration failure")
                        return cursor

                with patch(
                    "ingest.state.sqlite3.connect",
                    side_effect=lambda value: real_connect(
                        value, factory=FailingConnection
                    ),
                ):
                    with self.assertRaisesRegex(
                        sqlite3.OperationalError, "injected migration failure"
                    ):
                        IngestState(path)
                self.assertEqual(self.snapshot(path), original)
                with IngestState(path) as state:
                    self.assertEqual(
                        state.get("https://example.org/a", "kb-a"),
                        {"hash": "hash-a", "file_id": "file-a", "status": "ready"},
                    )
                    self.assertEqual(
                        state.get("https://example.org/b", "kb-b")["file_id"], "file-b"
                    )
                    self.assertIsNone(
                        state.db.execute(
                            "SELECT name FROM sqlite_master WHERE name='pages_legacy'"
                        ).fetchone()
                    )

    def test_constraint_failure_preserves_legacy_until_data_is_repaired(self):
        with TemporaryDirectory() as temp:
            path = Path(temp) / "state.sqlite3"
            self.create_legacy(path)
            with closing(sqlite3.connect(path)) as db, db:
                db.execute("UPDATE pages SET file_id=NULL WHERE knowledge_id='kb-a'")
            original = self.snapshot(path)
            with self.assertRaises(sqlite3.IntegrityError):
                IngestState(path)
            self.assertEqual(self.snapshot(path), original)
            with closing(sqlite3.connect(path)) as db, db:
                db.execute(
                    "UPDATE pages SET file_id='file-a' WHERE knowledge_id='kb-a'"
                )
            with IngestState(path) as state:
                self.assertEqual(
                    state.get("https://example.org/a", "kb-a")["status"], "ready"
                )
