# L-ai — Local AI with RAG

A **general-purpose local AI assistant** with chat and retrieval-augmented generation (**RAG**). Runs **Ollama + a configurable language model + Open WebUI** to search documents and answer questions across domains. Memory and accelerator requirements depend on the chosen model, context length, and runtime.

RAG does **not** train the model or modify its weights. It indexes authorized documents and retrieves relevant passages during conversations. The assistant is not restricted to a particular subject.

## Quick start

Requirements for the provided Bash setup: Bash, Git, OpenSSL, Docker Engine (or a compatible Docker runtime) with Compose v2, and sufficient storage and memory for the chosen model. Supported platforms depend on the installed Docker/Ollama runtime. Initial setup downloads container images and the model.

```bash
git clone https://github.com/hebermattos/L-ai.git
cd L-ai
bash scripts/setup.sh
docker compose ps
```

Open **http://localhost:3000**, create a local administrator account, and select the **lai** model. The script creates a secret in `.env`, starts Ollama and Open WebUI, downloads the selected Ollama model (Qwen by default), and configures the general-purpose `lai` profile. Do not run `sudo bash scripts/setup.sh`; configure Docker access using the [official documentation](https://docs.docker.com/engine/).

**Initial smoke test:** ask the model to explain a programming concept or summarize a general idea. This checks inference only, not RAG retrieval.

## Configurable model and hardware

The model is selectable: `qwen3:4b-instruct` is only the default. Set values in your local `.env` before running `bash scripts/setup.sh`:

```dotenv
L_AI_MODEL=qwen3:4b-instruct
L_AI_CONTEXT_LENGTH=8192
OLLAMA_NUM_PARALLEL=1
OLLAMA_MAX_LOADED_MODELS=1
```

The installer validates these values, pulls the requested model, and creates the local `lai` alias with a rendered Modelfile. The tracked `config/Modelfile` remains a template. Docker Compose reads the runtime concurrency settings from `.env`. Rerunning setup updates `lai` without deleting knowledge bases or Docker volumes. Model selection, context length, and concurrency are tunable defaults, not hardware minimums. Ollama can use a compatible GPU when the host runtime exposes it; GPU acceleration is opt-in through `L_AI_GPU=nvidia` or `L_AI_GPU=amd` on compatible hosts; it is not enabled by default.

For configuration details, see [model and resource settings](docs/model-configuration.md) and [platform and GPU setup](docs/platforms-and-gpu.md).

## Enable RAG

1. In Open WebUI, go to **Workspace → Knowledge** and create a knowledge base (for example, `Knowledge Library`).
2. Upload a small searchable PDF, TXT, or Markdown document.
3. In a chat with `lai`, attach that knowledge base using the knowledge selector (or `#` in compatible versions), or configure it on a custom model.
4. Ask a question whose answer occurs only in the document and verify that the correct source is cited. A plausible answer without a citation **does not prove RAG was used**.

For automated API ingestion, create an Open WebUI API key and obtain the knowledge-base ID. On the host:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-ingest.txt
export OPEN_WEBUI_API_KEY='YOUR_API_KEY'
export OPEN_WEBUI_KNOWLEDGE_ID='YOUR_KNOWLEDGE_BASE_ID'
```

Never commit credentials. The Docker setup does not install Python ingestion dependencies on the host.

## Import content

**One-command folder import** (recursive PDF/EPUB discovery plus two explicit URL lists):

```bash
python -m ingest.cli --import-folder ./knowledge-to-import --allow-domain example.org --dry-run
```

Once the preview is correct and Open WebUI credentials are configured, repeat without `--dry-run` to index all supported content. Place PDF/EPUB documents and these optional UTF-8 manifests anywhere under the import folder:

- `urls.txt`: fetch each listed HTTPS page exactly once (no link traversal).
- `crawl.txt`: recursively follow permitted internal HTML links from each listed HTTPS seed using `--max-depth` and `--max-pages`.

Both manifests accept one URL per line, blank lines, and `#` comments. Other `.txt` files are ignored in folder import. The crawler starts automatically for `crawl.txt` entries; **do not add `--crawl`** for folder manifests. The existing `--crawl` flag remains supported for explicit `--url` and `--urls-file` inputs. If a URL appears in both manifests, it is crawled once. URLs require explicit `--allow-domain` authorization and respect `robots.txt` and other safety limits.


**Individual web pages** from an explicitly authorized domain:

```bash
python -m ingest.cli --url https://example.org/article --allow-domain example.org --dry-run
```

**Controlled recursive crawler**, restricted to the starting host and directory:

```bash
python -m ingest.cli --url https://example.org/library/index --allow-domain example.org --crawl --max-depth 2 --max-pages 25 --dry-run
```

**Sitemap** and **explicit remote PDF** ingestion:

```bash
python -m ingest.cli --sitemap https://example.org/sitemap.xml --allow-domain example.org --max-pages 25 --dry-run
python -m ingest.cli --remote-pdf https://example.org/book.pdf --allow-domain example.org --dry-run
```

**Local PDF/EPUB books** and optional OCR for scanned PDFs:

```bash
python -m ingest.cli --directory ~/Books --max-documents 50 --dry-run
python -m ingest.cli --file ~/Documents/sample.pdf --ocr --dry-run
```

Replace `example.org` with a domain that explicitly permits collection. `--dry-run` extracts and previews content without uploading it. Remove the flag after setting the API key and knowledge-base ID. OCR additionally requires Tesseract and its language packages.

Web ingestion requires HTTPS, an explicit host allowlist and compliance with `robots.txt`; it rejects redirects and enforces depth and size limits. **It does not scrape arbitrary websites or execute dynamic JavaScript.** Remote PDF ingestion requires an explicit URL; the crawler does not automatically download linked PDFs.

## Query and verify

In Open WebUI, select `lai` and attach the imported knowledge base. Example prompts: “What requirements are described in this document?” and “Summarize chapter 2 and cite the source.”

For upload, indexing, and association tests against a **disposable knowledge base**, see [reliability testing](docs/reliability.md). These checks do not replace a semantic-retrieval test in chat.

## Documentation

- [Web ingestion and security](docs/web-ingestion.md) — URLs, sitemaps, limits, and permissions.
- [Crawler and local documents](docs/advanced-import.md) — traversal, PDF, EPUB, and OCR.
- [Reliability and testing](docs/reliability.md) — SQLite, updates, and recovery.
- [Knowledge pipeline and evaluation](docs/knowledge-pipeline.md) — scheduling, metadata, metrics, and hybrid search.
- [Platform and GPU setup](docs/platforms-and-gpu.md) — Linux, Windows/WSL2, macOS, and optional NVIDIA/AMD overlays.

## Operations and limitations

```bash
docker compose ps
docker compose logs --tail=100
docker compose stop
docker compose start
```

The chat binds to `127.0.0.1:3000`, while Ollama stays on the internal Docker network. The `ollama_data` and `open_webui_data` volumes persist models and data. Back up these volumes before upgrading; **do not run `docker compose down -v`** if you want to keep them. Do not expose the API or chat to the internet without additional security controls. Web collection needs network access; local inference requires no paid API.

Upgrade with `docker compose pull && docker compose up -d`, preferably using pinned image versions and verified backups. Performance and memory consumption depend on the selected model, processor, accelerator, and workload. OCR and large-scale indexing can be resource-intensive.

## Repository layout

```text
.
├── compose.yaml
├── .env.example
├── config/Modelfile
├── knowledge/                 # Local content and state, ignored by Git
├── ingest/                     # CLI, crawler, extractors, Open WebUI integration
├── requirements-ingest.txt
├── docs/                       # User and operations guides
├── scripts/setup.sh
├── scripts/check.sh
├── tests/
└── .github/workflows/ci.yml
```

References: [Ollama](https://ollama.com/library), [Open WebUI](https://docs.openwebui.com/), and [Docker](https://docs.docker.com/).

## Language policy

Source code, identifiers, comments, test names, CLI messages, model instructions and project documentation are maintained in **English**. The assistant can still respond in the user's requested language, including Brazilian Portuguese. Keep public CLI flags stable; see the migration instructions below for the renamed local storage directory.

## Upgrading the local knowledge directory

The local content and SQLite state directory is now `knowledge/`. On an existing installation, **back up your local data first**, then migrate the former directory before running ingestion:

```bash
bash scripts/migrate-knowledge.sh
```

The migration script renames the legacy `biblioteca/` directory only when `knowledge/` does not already exist. It refuses to merge directories or overwrite existing data. If both directories exist, inspect and reconcile them manually. The `--state` CLI option still accepts a custom database path.
