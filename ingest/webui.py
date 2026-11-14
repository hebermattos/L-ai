"""Open WebUI upload, async processing and Knowledge Base linking."""
from __future__ import annotations

import io
import time
from urllib.parse import urlsplit

import requests


class WebUIError(RuntimeError):
    pass


class WebUI:
    def __init__(self, base_url: str, api_key: str, knowledge_id: str):
        base = base_url.rstrip("/")
        parts = urlsplit(base)
        if parts.scheme != "http" or parts.hostname not in ("localhost", "127.0.0.1") or parts.port not in (None, 3000):
            raise ValueError("Only local http://localhost:3000 (or 127.0.0.1) is permitted")
        if not api_key or not knowledge_id or "/" in knowledge_id:
            raise ValueError("API key and knowledge ID are required")
        self.base = base
        self.knowledge_id = knowledge_id
        self.session = requests.Session()
        self.session.trust_env = False
        self.session.headers.update({"Authorization": f"Bearer {api_key}", "Accept": "application/json"})

    def _request(self, method: str, endpoint: str, **kwargs):
        try:
            response = self.session.request(
                method, self.base + endpoint, timeout=30, allow_redirects=False, **kwargs
            )
            if not (200 <= response.status_code < 300):
                raise WebUIError(f"Open WebUI {method} {endpoint}: HTTP {response.status_code}: {response.text[:300]}")
            return response.json()
        except (requests.RequestException, ValueError) as exc:
            raise WebUIError(f"Open WebUI request failed: {exc}") from exc

    def upload(self, name: str, markdown: str) -> str:
        payload = markdown.encode("utf-8")
        data = self._request(
            "POST", "/api/v1/files/",
            files={"file": (name, io.BytesIO(payload), "text/markdown")},
        )
        file_id = data.get("id")
        if not file_id:
            raise WebUIError("Upload response has no file ID")
        return file_id

    def wait_indexed(self, file_id: str, seconds: int = 180) -> None:
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            info = self._request("GET", f"/api/v1/files/{file_id}/process/status")
            status = info.get("status")
            if status == "completed":
                return
            if status == "failed":
                raise WebUIError(f"Embedding failed: {str(info.get('error'))[:300]}")
            time.sleep(2)
        raise WebUIError("Timed out waiting for embedding")

    def add_to_knowledge(self, file_id: str):
        return self._request(
            "POST", f"/api/v1/knowledge/{self.knowledge_id}/file/add",
            json={"file_id": file_id},
        )

    def update_content(self, file_id: str, markdown: str):
        return self._request(
            "POST", f"/api/v1/files/{file_id}/data/content/update",
            json={"content": markdown},
        )
