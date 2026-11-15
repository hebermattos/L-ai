# Reliability, failure recovery, and testing

L-ai maintains local SQLite state in `biblioteca/.web-ingest.sqlite3`, keyed by `(url, knowledge_id)`. The same source can therefore be used across multiple knowledge bases. Legacy schema migration is transactional; **back up SQLite before upgrading**.

## Ingestion states

- `uploaded`: the file was uploaded, but processing or knowledge-base association may be pending.
- `updating`: a remote-content update is pending or being verified.
- `ready`: the API confirmed content and association; **this does not prove semantic retrieval**.

Rerunning the same command can resume pending operations. Known risks: a crash after remote upload but before local state persistence can leave an orphaned file; do not share the state database across concurrent processes. Content verification depends on the installed Open WebUI API version and may change between releases.

## Isolated tests

```bash
python -m unittest discover -s tests -v
```

CI checks Compose configuration, shell syntax, and Python tests. Mocked API tests **do not launch** Ollama or Open WebUI.

## Optional live integration test (disposable knowledge base only)

Create an empty, disposable knowledge base and an API key with access in your local Open WebUI. Run from a terminal that can reach the instance:

```bash
export OPEN_WEBUI_API_KEY='YOUR_API_KEY'
export OPEN_WEBUI_KNOWLEDGE_ID='DISPOSABLE_KNOWLEDGE_BASE_ID'
L_AI_INTEGRATION=1 python -m unittest discover -s tests -p 'test_webui_integration.py' -v
```

The test uploads and updates a document. **It does not automatically delete the document**; remove it afterward through the UI. Never run this test against a production knowledge base.

For an **end-to-end RAG test**, attach the base to the chat, ask about a unique phrase in the test document, and check the response and citation. Repeat after updating the content and confirm the old passage is no longer retrieved. CI does not validate this semantic retrieval flow.

## Troubleshooting

If `docker compose ps` reports a stopped service, check `docker compose logs --tail=100`. If upload fails, verify the API key, knowledge-base ID, and API version. If answers lack citations, confirm that the base is attached to the chat and test retrieval of an exact passage. When releases behave differently, pin tested Docker image versions before modifying the code.

See [knowledge pipeline](knowledge-pipeline.md) and [installation](../README.md).
