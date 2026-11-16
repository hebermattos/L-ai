# Reliability, failure recovery, and testing

L-ai maintains local SQLite state in `knowledge/.web-ingest.sqlite3`, keyed by `(url, knowledge_id)`. The same source can therefore be used across multiple knowledge bases. Legacy schema migration is transactional; **back up SQLite before upgrading**.

## Operations and upgrades

Run manual Compose commands from the repository root. Select the same files used by your deployment:

| Backend | Compose command prefix |
| --- | --- |
| Default (`none`) | `docker compose -f compose.yaml` |
| NVIDIA | `docker compose -f compose.yaml -f compose.gpu.nvidia.yaml` |
| AMD | `docker compose -f compose.yaml -f compose.gpu.amd.yaml` |

Append `ps`, `logs --tail=100`, `stop`, or `start` to that prefix for routine operations. Setting `L_AI_GPU` in `.env` does not make plain `docker compose` load an overlay; setup selects it only for its own subprocesses.

Back up first, then pull and recreate with the matching command pair:

```bash
# Default backend
docker compose -f compose.yaml pull
docker compose -f compose.yaml up -d

# NVIDIA backend
docker compose -f compose.yaml -f compose.gpu.nvidia.yaml pull
docker compose -f compose.yaml -f compose.gpu.nvidia.yaml up -d

# AMD backend
docker compose -f compose.yaml -f compose.gpu.amd.yaml pull
docker compose -f compose.yaml -f compose.gpu.amd.yaml up -d
```

Run only the pair matching your backend. The repository uses moving image tags (`latest`, `main`, and `rocm`); pin tested versions for repeatable upgrades. After an upgrade, check service logs and repeat the citation test in the [README](../README.md#enable-rag). Changing model or context settings additionally requires `bash scripts/setup.sh` to recreate `lai`.

## Backup and persistence

The `ollama_data` and `open_webui_data` named volumes persist models, conversations, and knowledge data. Their Docker names normally include the Compose project prefix. Ingestion state is stored separately on the host in `knowledge/`, or at the custom `--state` path.

Stop ingestion and the stack before taking consistent backups. Back up both volumes, the local state directory, and `.env` using your Docker volume backup procedure; protect credentials and confirm that the backup can be restored. Copying the repository alone does not back up container volumes. SQLite may have WAL sidecar files, so do not copy only an active database file. Avoid `docker compose down -v`: it deletes the named volumes. Do not expose the chat or API to the internet without additional access controls.

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

Use the matching Compose prefix above with `ps` and `logs --tail=100` to investigate stopped services. If upload fails, verify the API key, knowledge-base ID, and API version. If answers lack citations, confirm that the base is attached to the chat and test retrieval of an exact passage. When releases behave differently, pin tested Docker image versions before modifying the code.

See [knowledge pipeline](knowledge-pipeline.md) and [installation](../README.md).

## Directory migration

The default state directory is `knowledge/`. For previous installations using `biblioteca/`, back up the local data and run `bash scripts/migrate-knowledge.sh` before ingestion. The script renames the legacy directory only when `knowledge/` does not exist; it refuses to merge directories or overwrite data. When both directories exist, reconcile them manually; the ingestion CLI accepts `--state` to select a database explicitly.
