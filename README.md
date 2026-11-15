# L-ai — Local AI with RAG

A **general-purpose**, fully local chat assistant with retrieval-augmented generation (**RAG**). Uses **Ollama + Qwen3 4B Instruct + Open WebUI** to query your documents across different subjects. Designed for Linux systems with **CPU and 16 GB RAM**; no GPU required.

RAG does **not** train or modify model weights. It indexes authorized documents and retrieves relevant excerpts at question time. L-ai is not restricted to a particular subject.

## Quick start

Requirements: Ubuntu/Debian, Docker Engine with Compose v2, Git, OpenSSL, Docker access, and sufficient disk space. The initial setup downloads images and the model.

```bash
git clone https://github.com/hebermattos/L-ai.git
cd L-ai
bash scripts/setup.sh
docker compose ps
```

Open **http://localhost:3000**, create a local administrator, and select the **lai** model. The setup script generates an untracked secret in `.env`, starts Ollama/Open WebUI, downloads Qwen, and creates the generic `lai` profile. Do not run `sudo bash scripts/setup.sh`; configure Docker access using the [official instructions](https://docs.docker.com/engine/install/linux-postinstall/).

**Smoke test:** ask the model to explain a programming concept. This tests inference, **not** RAG retrieval.

## Enable RAG

1. In Open WebUI, go to **Workspace → Knowledge** and create a knowledge base such as `Knowledge Library`.
2. Upload a small text-based PDF, TXT, or Markdown file.
3. In the `lai` chat, attach the knowledge base using the knowledge selector (in supported versions, type `#`), or associate it with a custom model.
4. Ask a question answered **only** in the document, and verify the source attribution. A plausible answer without a citation does **not** prove RAG was used.

For automated ingestion, create an API key in Open WebUI and obtain the knowledge-base ID:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-ingest.txt
export OPEN_WEBUI_API_KEY='YOUR_API_KEY'
export OPEN_WEBUI_KNOWLEDGE_ID='YOUR_KNOWLEDGE_BASE_ID'
```

Never commit credentials. The Docker setup does not install the host-side Python ingestion dependencies.

## Import content

**Individual authorized HTTPS pages:**

```bash
python -m ingest.cli --url https://example.org/article --allow-domain example.org --dry-run
```

**Bounded recursive crawler** (same host and seed directory):

```bash
python -m ingest.cli --url https://example.org/library/index --allow-domain example.org --crawl --max-depth 2 --max-pages 25 --dry-run
```

**Sitemaps and explicitly provided remote PDFs:**

```bash
python -m ingest.cli --sitemap https://example.org/sitemap.xml --allow-domain example.org --max-pages 25 --dry-run
python -m ingest.cli --remote-pdf https://example.org/book.pdf --allow-domain example.org --dry-run
```

**Local PDF/EPUB books and optional scanned-PDF OCR:**

```bash
python -m ingest.cli --directory ~/Books --max-documents 50 --dry-run
python -m ingest.cli --file ~/Documents/scanned.pdf --ocr --dry-run
```

Replace `example.org` with a site you are authorized to collect. `--dry-run` extracts and reports without uploading; remove it only after configuring the API key and knowledge-base ID. OCR requires separately installed Tesseract and language packs.

Web ingestion requires HTTPS, explicitly allowed hosts and compliance with `robots.txt`; it rejects redirects and bounds depth, size, and volume. **It does not support arbitrary-site scraping or JavaScript-rendered sites.** Remote PDFs must be supplied explicitly; crawling does not automatically download linked PDFs.

## Query and verify

Select `lai` in Open WebUI and attach the imported knowledge base. Example questions: “What requirements does this document describe?” or “Summarize chapter 2 and cite the source.”

For a real upload/index/link test against a **disposable** knowledge base, see [reliability testing](docs/reliability.md). This is not a substitute for semantic retrieval verification in chat.

## Documentation

- [Web ingestion and safeguards](docs/web-ingestion.md): URLs, sitemaps, limits, permissions.
- [Crawler and local documents](docs/advanced-import.md): navigation, PDF, EPUB, OCR.
- [Reliability and tests](docs/reliability.md): SQLite, updates, recovery.
- [Knowledge pipeline and evaluation](docs/knowledge-pipeline.md): schedules, metadata, retrieval metrics, hybrid search.

## Operations and limitations

```bash
docker compose ps
docker compose logs --tail=100
docker compose stop
docker compose start
```

The chat binds to `127.0.0.1:3000`; Ollama stays on the internal Docker network. Persistent volumes `ollama_data` and `open_webui_data` contain the model and application data. Back them up before upgrades. **Do not use `docker compose down -v`** unless you intend to delete these volumes. Do not expose the service to the internet without additional access controls. Web ingestion needs outbound network access; local inference requires no paid API.

Upgrade with `docker compose pull && docker compose up -d`, preferably after backing up and pinning tested image versions. CPU speed determines performance; large-scale OCR and indexing may be slow.

## Repository layout

```text
.
├── compose.yaml
├── .env.example
├── config/Modelfile
├── biblioteca/                 # Local content and state; ignored by Git
├── ingest/                     # CLI, crawler, extractors, Open WebUI integration
├── requirements-ingest.txt
├── docs/                       # Usage guides
├── scripts/setup.sh
├── scripts/check.sh
├── tests/
└── .github/workflows/ci.yml
```

References: [Ollama](https://ollama.com/library/qwen3:4b-instruct), [Open WebUI](https://docs.openwebui.com/), and [Docker](https://docs.docker.com/engine/install/ubuntu/).

## Language policy

Source code, identifiers, comments, test names, CLI messages, model instructions and project documentation are maintained in **English**. The assistant can still respond in the user's requested language, including Brazilian Portuguese. Keep public CLI flags and existing storage identifiers stable for compatibility.
