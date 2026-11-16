# Model and resource configuration

L-ai uses Ollama and Open WebUI. It has no fixed CPU-only or 16 GB RAM requirement: actual capacity depends on model size, quantization, context length, concurrency, and available CPU/GPU memory.

## Configure the model

After creating the local `.env`, set these optional variables:

```dotenv
L_AI_MODEL=qwen3:4b-instruct
L_AI_CONTEXT_LENGTH=8192
OLLAMA_NUM_PARALLEL=1
OLLAMA_MAX_LOADED_MODELS=1
```

- `L_AI_MODEL` is the Ollama model reference to download and use as the basis of the `lai` assistant.
- `L_AI_CONTEXT_LENGTH` sets the `PARAMETER num_ctx` value when the local assistant is created.
- `OLLAMA_NUM_PARALLEL` and `OLLAMA_MAX_LOADED_MODELS` control Ollama runtime concurrency in Docker Compose.

All four values have backward-compatible defaults. The installer only reads explicitly named settings from `.env`, validates the model reference and positive integer fields, and renders the default Modelfile into a temporary file. It does not modify the checked-in `config/Modelfile` or remove Docker volumes.

To apply configuration changes:

```bash
bash scripts/setup.sh
docker compose ps
```

Changing the model may require a significant download and more memory or storage. Existing conversations and knowledge content are stored separately from the generated model alias; make a backup before major changes.

## Platform and acceleration

The provided setup script requires Bash, OpenSSL, Docker Compose v2, and access to a working Docker daemon. It is suitable for environments providing these tools, but the project does not claim that every operating system or GPU configuration has been tested.

The default Compose stack does not request GPU devices. Ollama may use acceleration when a supported accelerator is correctly exposed to the container runtime. Configure drivers, passthrough, and runtime integration separately for your platform. CPU execution remains supported when the model fits available memory.

## Resource planning

Choose model quantization and context size based on available RAM/VRAM. Larger context windows and multiple parallel requests generally require more memory. Reduce `L_AI_CONTEXT_LENGTH`, `OLLAMA_NUM_PARALLEL`, or `OLLAMA_MAX_LOADED_MODELS` when resources are constrained. The included values are operational defaults rather than a guaranteed minimum or universal optimum.
