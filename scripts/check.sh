#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
docker compose ps
docker compose exec -T ollama ollama list
echo "Verificando Open WebUI..."
curl --fail --silent --show-error --max-time 10 http://127.0.0.1:3000/ >/dev/null
echo "Open WebUI responde em http://localhost:3000"
