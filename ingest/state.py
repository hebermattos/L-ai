"""Durable per-(URL, KB) ingest state with migration of the original schema."""
import sqlite3
from pathlib import Path
from types import TracebackType
from typing import cast

from .contracts import IngestStatus, PageState

class IngestState:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path)
        try:
            self.db.execute("PRAGMA busy_timeout=5000")
            self.db.execute("PRAGMA journal_mode=WAL")
            self.migrate()
        except Exception:
            self.db.close()
            raise

    def migrate(self) -> None:
        self.db.execute("BEGIN IMMEDIATE")
        try:
            exists = self.db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='pages'").fetchone()
            if exists:
                details = list(self.db.execute("PRAGMA table_info(pages)"))
                pk = [row[1] for row in sorted(details, key=lambda row: row[5]) if row[5]]
                if pk != ['url', 'knowledge_id'] or 'status' not in {r[1] for r in details}:
                    self.db.execute("ALTER TABLE pages RENAME TO pages_legacy")
                    self._create()
                    self.db.execute("""INSERT INTO pages(url,knowledge_id,hash,file_id,status)
                        SELECT url,knowledge_id,hash,file_id,'ready' FROM pages_legacy""")
                    self.db.execute("DROP TABLE pages_legacy")
            else:
                self._create()
            self.db.execute("CREATE INDEX IF NOT EXISTS pages_hash_idx ON pages(knowledge_id,hash,status)")
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

    def _create(self) -> None:
        self.db.execute("""CREATE TABLE pages(
            url TEXT NOT NULL, knowledge_id TEXT NOT NULL, hash TEXT NOT NULL,
            file_id TEXT NOT NULL, status TEXT NOT NULL
            CHECK(status IN ('uploaded','updating','ready')),
            PRIMARY KEY(url,knowledge_id))""")

    def get(self, url: str, knowledge_id: str) -> PageState | None:
        row = self.db.execute("SELECT hash,file_id,status FROM pages WHERE url=? AND knowledge_id=?",
                              (url, knowledge_id)).fetchone()
        return cast(PageState, dict(zip(('hash','file_id','status'), row))) if row else None

    def duplicate(self, digest: str, knowledge_id: str, except_url: str) -> tuple[str] | None:
        row = self.db.execute("""SELECT file_id FROM pages WHERE knowledge_id=? AND hash=?
            AND status='ready' AND url<>? LIMIT 1""", (knowledge_id,digest,except_url)).fetchone()
        return cast(tuple[str] | None, row)

    def save(self, url: str, knowledge_id: str, digest: str,
             file_id: str, status: IngestStatus) -> None:
        if status not in ('uploaded','updating','ready'):
            raise ValueError("Invalid ingestion status")
        with self.db:
            self.db.execute("""INSERT INTO pages(url,knowledge_id,hash,file_id,status) VALUES (?,?,?,?,?)
                ON CONFLICT(url,knowledge_id) DO UPDATE SET
                hash=excluded.hash,file_id=excluded.file_id,status=excluded.status""",
                (url,knowledge_id,digest,file_id,status))

    def close(self) -> None:
        self.db.close()

    def __enter__(self) -> "IngestState":
        return self

    def __exit__(self, exc_type: type[BaseException] | None,
                 exc_value: BaseException | None,
                 traceback: TracebackType | None) -> None:
        self.close()
