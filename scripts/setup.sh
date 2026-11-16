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

# Read only the known configuration values; do not execute .env as shell code.
read_env_setting() {
  local key="$1"
  if [[ -f .env ]]; then
    sed -n "s/^${key}=//p" .env | tail -n 1 | tr -d '\r'
  fi
}

model="${L_AI_MODEL:-$(read_env_setting L_AI_MODEL)}"
model="${model:-qwen3:4b-instruct}"
context_length="${L_AI_CONTEXT_LENGTH:-$(read_env_setting L_AI_CONTEXT_LENGTH)}"
context_length="${context_length:-8192}"
num_parallel="${OLLAMA_NUM_PARALLEL:-$(read_env_setting OLLAMA_NUM_PARALLEL)}"
num_parallel="${num_parallel:-1}"
max_loaded_models="${OLLAMA_MAX_LOADED_MODELS:-$(read_env_setting OLLAMA_MAX_LOADED_MODELS)}"
max_loaded_models="${max_loaded_models:-1}"

if [[ ! "$model" =~ ^[a-zA-Z0-9][a-zA-Z0-9._:/-]*$ ]]; then
  echo "L_AI_MODEL must be a valid Ollama model reference." >&2
  exit 1
fi
for value in "$context_length" "$num_parallel" "$max_loaded_models"; do
  if [[ ! "$value" =~ ^[1-9][0-9]*$ ]]; then
    echo "Context length and concurrency limits must be positive integers." >&2
    exit 1
  fi
done

# Explicit overrides are also forwarded to Compose, which otherwise reads .env.
export OLLAMA_NUM_PARALLEL="$num_parallel"
export OLLAMA_MAX_LOADED_MODELS="$max_loaded_models"

# Render a temporary model configuration, leaving the tracked template intact.
generated_modelfile="$(mktemp)"
trap 'rm -f "$generated_modelfile"' EXIT
sed -e "1s|^FROM .*|FROM ${model}|" \
    -e "s|^PARAMETER num_ctx .*|PARAMETER num_ctx ${context_length}|" \
    config/Modelfile > "$generated_modelfile"

docker compose up -d
docker compose exec -T ollama ollama pull "$model"
docker compose exec -T ollama sh -c 'cat > /tmp/lai-Modelfile && ollama create lai -f /tmp/lai-Modelfile' < "$generated_modelfile"

echo
echo "Setup complete. Open http://localhost:3000 and select the lai model."
echo "Import documents under Workspace -> Knowledge to enable RAG."
