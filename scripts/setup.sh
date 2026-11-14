#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker não encontrado. Instale Docker Engine e Compose v2." >&2
  exit 1
fi
if ! docker compose version >/dev/null 2>&1; then
  echo "Plugin Docker Compose v2 não encontrado." >&2
  exit 1
fi
if ! command -v openssl >/dev/null 2>&1; then
  echo "OpenSSL não encontrado; instale openssl para gerar a chave local." >&2
  exit 1
fi
if [[ ! -f .env ]]; then
  umask 077
  printf 'WEBUI_SECRET_KEY=%s\n' "$(openssl rand -hex 32)" > .env
  echo "Segredo gerado em .env (não versionado)."
fi

if grep -q 'replace-me-with-a-random-secret' .env; then
  echo "Substitua a chave de exemplo em .env por uma chave aleatória." >&2
  exit 1
fi

docker compose up -d
docker compose exec -T ollama ollama pull qwen3:4b-instruct
docker compose exec -T ollama ollama create arcana -f /config/Modelfile

echo
echo "Instalação configurada. Abra http://localhost:3000"
echo "Importe seus documentos em Workspace -> Knowledge para habilitar RAG."
