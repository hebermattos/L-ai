"""Internal types that retain existing SQLite values and public result strings."""

from typing import Literal, Protocol, TypedDict

IngestStatus = Literal["uploaded", "updating", "ready"]
IngestResult = Literal[
    "UNCHANGED", "RECOVERED", "UPDATED", "DUPLICATE CONTENT", "IMPORTED"
]


class PageState(TypedDict):
    hash: str
    file_id: str
    status: IngestStatus


class StateStore(Protocol):
    def get(self, url: str, knowledge_id: str) -> PageState | None: ...
    def duplicate(self, digest: str, knowledge_id: str, except_url: str) -> object: ...
    def save(
        self,
        url: str,
        knowledge_id: str,
        digest: str,
        file_id: str,
        status: IngestStatus,
    ) -> None: ...


class KnowledgeClient(Protocol):
    knowledge_id: str

    def knowledge_has_file(self, file_id: str) -> bool: ...
    def wait_indexed(self, file_id: str) -> None: ...
    def ensure_linked(self, file_id: str) -> None: ...
    def update_content(self, file_id: str, markdown: str) -> None: ...
    def upload(self, name: str, markdown: str) -> str: ...
