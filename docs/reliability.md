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

CI checks Compose configuration, all Bash scripts with syntax checks and ShellCheck,
and Python tests on Linux, Windows, and macOS. POSIX script execution tests run on
Linux and macOS; Windows skips those tests explicitly. Symlink tests are skipped
only when the Windows runner reports missing symlink privileges. Mocked API tests **do not launch** Ollama or Open WebUI.

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


## Development checks

Install development dependencies in a virtual environment and run the same Python checks as CI:

```bash
python -m pip install -r requirements-dev.txt
python -m ruff check ingest tests
python -m mypy
python -m unittest discover -s tests -v
python -m compileall -q ingest tests
# In a POSIX Bash environment:
for script in scripts/*.sh; do bash -n "$script"; done
shellcheck scripts/*.sh
```

Ruff checks unused imports and other Python errors. Strict type checking covers
`contracts.py`, `state.py`, `service.py`, `manifests.py`, `cli.py`, `crawler.py`,
`sitemap.py`, and `webui.py`; extend its scope as other modules gain complete annotations. Development tools are separate from runtime dependencies.

The CLI separates input preparation from source execution. Local and remote PDFs
share page-text extraction, while keeping their existing OCR policies, metadata
fallbacks, and error messages. URL manifest parsing is shared; each entry point
retains its own byte and count limits. SQLite connections and Open WebUI sessions
support context managers and are closed by the CLI, including on processing errors.

Behavior tests cover CLI output and exit codes, document formatting, source ordering,
body hashes, filenames, and the existing SQLite schema. Network timing tests inject
clocks and sleep functions; production defaults retain the existing pauses and timeouts.
The live Open WebUI test remains opt-in and requires a disposable knowledge base.


Folder discovery stops after the first entry beyond the 1,000-entry limit, before
sorting, while accepted folders retain their previous sorted import order. Sitemap
queues deduplicate both seeds and discovered maps before enqueueing, retaining the
first-discovery order and the existing unique-map and page budgets.

Pagination tests cover array and object responses, `items` and `files`, `has_more`,
`total`, missing files, malformed payloads, and exhausted pagination limits. Migration
tests inject failures after each transactional schema/data operation and exercise a
real constraint violation, then verify unchanged legacy schema/data and successful retry.
