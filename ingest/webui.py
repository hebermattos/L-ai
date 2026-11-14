"""Local Open WebUI upload, processing, association and update verification."""
import io
import time
from urllib.parse import urlsplit
import requests

class WebUIError(RuntimeError):
    pass

class WebUI:
    def __init__(self, base_url, api_key, knowledge_id):
        base = base_url.rstrip('/')
        p = urlsplit(base)
        if (p.scheme != 'http' or p.hostname not in ('localhost','127.0.0.1')
                or p.port not in (None,3000) or p.path or p.query or p.fragment
                or p.username or p.password):
            raise ValueError("Only http://localhost:3000 (or 127.0.0.1) is allowed")
        if not api_key or not knowledge_id or not all(c.isalnum() or c in '-_' for c in knowledge_id):
            raise ValueError("Valid API key and Knowledge ID are required")
        self.base = base
        self.knowledge_id = knowledge_id
        self.session = requests.Session()
        self.session.trust_env = False
        self.session.headers.update({'Authorization': f'Bearer {api_key}', 'Accept':'application/json'})

    def _request(self, method, endpoint, **kwargs):
        try:
            response = self.session.request(method, self.base+endpoint, timeout=30,
                                            allow_redirects=False, **kwargs)
        except requests.RequestException as exc:
            raise WebUIError(f"Open WebUI network failure: {exc}") from exc
        if not 200 <= response.status_code < 300:
            raise WebUIError(f"Open WebUI {method} {endpoint}: HTTP {response.status_code}: {response.text[:300]}")
        try:
            return response.json()
        except ValueError as exc:
            raise WebUIError("Open WebUI returned invalid JSON") from exc

    def upload(self, name, markdown):
        data = self._request('POST','/api/v1/files/', files={
            'file':(name, io.BytesIO(markdown.encode('utf-8')), 'text/markdown')})
        file_id = data.get('id') if isinstance(data,dict) else None
        if not isinstance(file_id,str) or not file_id:
            raise WebUIError("Upload response lacks file ID")
        return file_id

    def wait_indexed(self, file_id, seconds=180):
        deadline = time.monotonic()+seconds
        while time.monotonic()<deadline:
            info = self._request('GET',f'/api/v1/files/{file_id}/process/status')
            status = info.get('status') if isinstance(info,dict) else None
            if status == 'completed':
                return
            if status == 'failed':
                raise WebUIError(f"Processing failed: {str(info.get('error'))[:300]}")
            time.sleep(2)
        raise WebUIError("Timed out waiting for file processing")

    def knowledge_has_file(self, file_id, max_pages=100):
        for page in range(1,max_pages+1):
            data = self._request('GET',f'/api/v1/knowledge/{self.knowledge_id}/files',
                                 params={'page':page})
            if isinstance(data,list):
                files = data
            elif isinstance(data,dict):
                files = data.get('files',data.get('items',[]))
            else:
                raise WebUIError("Unexpected Knowledge list response")
            if not isinstance(files,list):
                raise WebUIError("Unexpected Knowledge files payload")
            if any(isinstance(f,dict) and (f.get('id')==file_id or f.get('file_id')==file_id)
                   for f in files):
                return True
            if isinstance(data,dict) and data.get('has_more') is True:
                continue
            if isinstance(data,dict) and isinstance(data.get('total'),int) and files:
                if page*len(files) < data['total']:
                    continue
            # In some releases the endpoint returns an array without pagination info.
            if len(files) >= 50:
                continue
            return False
        raise WebUIError("Exceeded Knowledge pagination limit")

    def add_to_knowledge(self, file_id):
        """Backwards compatible P0 API."""
        return self._request('POST',f'/api/v1/knowledge/{self.knowledge_id}/file/add',
                             json={'file_id':file_id})

    def ensure_linked(self, file_id):
        if self.knowledge_has_file(file_id):
            return
        self.add_to_knowledge(file_id)
        if not self.knowledge_has_file(file_id):
            raise WebUIError("Knowledge membership not confirmed")

    def verify_content(self, file_id, expected):
        data = self._request('GET',f'/api/v1/files/{file_id}/data/content')
        actual = data.get('content') if isinstance(data,dict) else data
        if actual != expected:
            raise WebUIError("Remote content differs from expected update")

    def update_content(self, file_id, markdown):
        # Open WebUI reprocesses KB vectors for content updates. On failures
        # keep the local operation pending rather than marking it complete.
        self._request('POST',f'/api/v1/files/{file_id}/data/content/update',
                      json={'content':markdown})
        self.verify_content(file_id,markdown)
        if not self.knowledge_has_file(file_id):
            raise WebUIError("Updated file is no longer linked to Knowledge")
