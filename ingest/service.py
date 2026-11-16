"""Resumable ingest workflow; save remote IDs before processing and linking."""
import hashlib

from .contracts import IngestResult, KnowledgeClient, StateStore

def ingest_page(state: StateStore, webui: KnowledgeClient, url: str, title: str,
                body: str, document: str) -> IngestResult:
    kb = webui.knowledge_id
    digest = hashlib.sha256(body.encode('utf-8')).hexdigest()
    old = state.get(url, kb)

    if old and old['hash'] == digest and old['status'] == 'ready':
        if webui.knowledge_has_file(old['file_id']):
            return 'UNCHANGED'
        state.save(url, kb, digest, old['file_id'], 'uploaded')
        old = state.get(url, kb)

    if old and old['status'] == 'uploaded':
        file_id = old['file_id']
        webui.wait_indexed(file_id)
        webui.ensure_linked(file_id)
        if old['hash'] == digest:
            state.save(url, kb, digest, file_id, 'ready')
            return 'RECOVERED'
        # Content changed while the prior upload/link operation was pending.
        state.save(url, kb, old['hash'], file_id, 'ready')
        old = state.get(url, kb)

    if old:
        # Store pending update before calling remote endpoint; repeat on retry.
        state.save(url, kb, digest, old['file_id'], 'updating')
        webui.update_content(old['file_id'], document)
        state.save(url, kb, digest, old['file_id'], 'ready')
        return 'UPDATED'

    if state.duplicate(digest, kb, except_url=url):
        return 'DUPLICATE CONTENT'

    filename = hashlib.sha256(url.encode('utf-8')).hexdigest()[:20] + '.md'
    file_id = webui.upload(filename, document)
    state.save(url, kb, digest, file_id, 'uploaded')
    webui.wait_indexed(file_id)
    webui.ensure_linked(file_id)
    state.save(url, kb, digest, file_id, 'ready')
    return 'IMPORTED'
