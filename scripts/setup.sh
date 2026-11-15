#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker not found. Install Docker Engine and Compose v2." >&2
  exit 1
fi
if ! docker compose version >/dev/null 2>&1; then
  echo "Docker Compose v2 plugin not found." >&2
  exit 1
fi
if ! command -v openssl >/dev/null 2>&1; then
  echo "OpenSSL not found; install openssl to generate a local secret." >&2
  exit 1
fi
if [[ ! -f .env ]]; then
  umask 077
  printf 'WEBUI_SECRET_KEY=%s\n' "$(openssl rand -hex 32)" > .env
  echo "Secret generated in .env (not tracked by Git)."
fi

if grep -q 'replace-me-with-a-random-secret' .env; then
  echo "Replace the example secret in .env with a random value." >&2
  exit 1
fi

docker compose up -d
docker compose exec -T ollama ollama pull qwen3:4b-instruct
docker compose exec -T ollama ollama create lai -f /config/Modelfile

echo
echo "Setup complete. Open http://localhost:3000 and select the lai model."
echo "Import documents under Workspace -> Knowledge to enable RAG."
