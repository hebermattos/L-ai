# L-ai — Local AI with RAG

A **general-purpose local AI assistant** using Ollama, a configurable language model, and Open WebUI. Chat with the model or attach documents through retrieval-augmented generation (**RAG**). RAG retrieves passages during conversations; it does not train the model or change its weights.

## Quick start

Install Bash, Git, OpenSSL, and Docker with Compose v2. Memory and storage requirements depend on the selected model and workload. For Windows/WSL2, macOS, or GPU acceleration, see [platform setup](docs/platforms-and-gpu.md).

```bash
git clone https://github.com/hebermattos/L-ai.git
cd L-ai
bash scripts/setup.sh
docker compose ps
```

Open **http://localhost:3000**, create a local administrator account, and select **lai**. Setup generates a secret in `.env`, starts the containers, downloads the default model, and creates the `lai` profile. Initial downloads require internet access. Do not run setup with `sudo`; configure Docker access first.

Ask a general question to check inference. To choose another model, context length, or GPU backend, edit `.env` and rerun setup; see [model configuration](docs/model-configuration.md).

## Enable RAG

1. In Open WebUI, open **Workspace → Knowledge** and create a knowledge base.
2. Upload a small searchable PDF, TXT, or Markdown document.
3. In a chat with `lai`, attach the base through the knowledge selector (or `#` in compatible versions), or configure it on a custom model.
4. Ask something answered only in that document and verify the cited source. A plausible answer alone does not prove retrieval worked.

For CLI imports, install Python dependencies on the host and configure an Open WebUI API key and knowledge-base ID:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-ingest.txt
export OPEN_WEBUI_API_KEY='YOUR_API_KEY'
export OPEN_WEBUI_KNOWLEDGE_ID='YOUR_KNOWLEDGE_BASE_ID'
```

Never commit credentials. The CLI uses the local Open WebUI instance at `http://127.0.0.1:3000`.

## Import content

Put PDF/EPUB files and optional UTF-8 URL lists in a folder, including subfolders:

```text
knowledge-to-import/
├── manual.pdf
├── reference.epub
├── urls.txt       # One HTTPS page per line; no link traversal
└── crawl.txt      # One HTTPS crawler seed per line
```

```bash
python -m ingest.cli --import-folder ./knowledge-to-import --allow-domain example.org --dry-run
```

Replace `example.org` with an authorized domain; repeat `--allow-domain` for additional hosts. Local-only imports need no domain. Lists accept blank lines and `#` comments. Other TXT files are ignored by folder import; PDF/EPUB are the CLI's supported local document formats.

`--dry-run` downloads and extracts sources, then reports source, title, and character count. It does not display extracted passages, upload content, or save ingestion state. Remove it to index content after configuring credentials. Attach the resulting knowledge base to the chat and verify citations.

See the [import guide](docs/advanced-import.md) for individual files and URLs, `--crawl`, `--sitemap`, `--ocr`, and all limits.

## Documentation

| Guide | Contents |
| --- | --- |
| [Import content](docs/advanced-import.md) | Folder manifests, web sources, PDF/EPUB, OCR, and limits |
| [Model configuration](docs/model-configuration.md) | Variables, defaults, and resource planning |
| [Platform and GPU setup](docs/platforms-and-gpu.md) | Linux, Windows/WSL2, macOS, NVIDIA, and AMD |
| [Operations and reliability](docs/reliability.md) | Start/stop, upgrades, backup, migration, recovery, and tests |
| [Knowledge pipeline](docs/knowledge-pipeline.md) | Provenance, incremental updates, scheduling, and evaluation |

The chat binds to `127.0.0.1:3000`; Ollama stays on the Docker network. Models and Open WebUI data persist in named volumes. See [maintenance instructions](docs/reliability.md#operations-and-upgrades) before upgrading or changing a GPU deployment.

## Repository layout

```text
.
├── compose.yaml
├── compose.gpu.nvidia.yaml
├── compose.gpu.amd.yaml
├── .env.example
├── config/Modelfile
├── knowledge/                 # Local content and state, ignored by Git
├── ingest/                    # CLI, crawler, extractors, Open WebUI integration
├── requirements-ingest.txt
├── docs/
├── scripts/
├── tests/
└── .github/workflows/ci.yml
```

## Language policy

Maintain code, identifiers, comments, CLI messages, model instructions, and documentation in **English**. The assistant can answer in the user's requested language, including Brazilian Portuguese.

References: [Ollama](https://ollama.com/library), [Open WebUI](https://docs.openwebui.com/), and [Docker](https://docs.docker.com/).
