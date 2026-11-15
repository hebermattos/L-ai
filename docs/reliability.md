# Reliability, recovery and tests

L-ai stores local ingestion state in SQLite at `biblioteca/.web-ingest.sqlite3`, keyed by `(url, knowledge_id)`. This supports reusing a source across separate knowledge bases. Legacy-schema migration is transactional; **back up SQLite before upgrading**.

## State transitions

- `uploaded`: file uploaded, but processing or knowledge-base association may still be pending.
- `updating`: a remote content update is pending or under verification.
- `ready`: the API confirmed content and association; this **does not prove semantic retrieval**.

Repeating the command may resume pending work. Known risks: crashes between remote upload and local state persistence may leave an orphaned file; never use the same state database concurrently from two processes. Content validation depends on the API endpoints of the installed Open WebUI version, which may change.

## Isolated tests

```bash
python -m unittest discover -s tests -v
```

CI checks Docker Compose configuration, shell syntax and Python tests. Mocked API tests **do not launch** Ollama or Open WebUI.

## Optional live integration test (disposable knowledge base only)

Create an empty, disposable knowledge base and an authorized API key in your local Open WebUI instance:

```bash
export OPEN_WEBUI_API_KEY='YOUR_API_KEY'
export OPEN_WEBUI_KNOWLEDGE_ID='DISPOSABLE_KNOWLEDGE_BASE_ID'
L_AI_INTEGRATION=1 python -m unittest discover -s tests -p 'test_webui_integration.py' -v
```

This test uploads and updates a document. **It does not delete it automatically**; delete it in the UI afterward. Do not target a production knowledge base.

For an **end-to-end RAG test**, attach the knowledge base to a chat, ask about a unique phrase in the test document, and inspect the answer and citations. Repeat after updating the document and confirm the old passage is no longer retrieved. CI does not cover this semantic retrieval flow.

## Troubleshooting

If `docker compose ps` reports a stopped service, inspect `docker compose logs --tail=100`. For upload failures, check the API key, knowledge-base ID, and API version. For answers with no citations, verify the chat's knowledge-base association and try an exact known passage. Pin tested Docker image versions before making code changes for API differences between releases.

See [pipeline and evaluation](knowledge-pipeline.md) and [setup](../README.md).
