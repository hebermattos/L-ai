# Platform and GPU setup

L-ai runs Ollama and Open WebUI through Docker Compose. Hardware compatibility is determined by the chosen model and host runtime. The default configuration requires no GPU passthrough.

## Platform guidance

| Platform | Default Docker stack | GPU acceleration in Docker |
| --- | --- | --- |
| Linux | Run `bash scripts/setup.sh` with Docker Engine and Compose v2 | NVIDIA via NVIDIA Container Toolkit; compatible AMD ROCm GPUs via Linux device passthrough |
| Windows with WSL2 | Run the script inside a WSL2 Linux shell with Docker Desktop's WSL2 backend | NVIDIA passthrough when supported by the driver, WSL2, Docker Desktop, and container runtime |
| macOS | Run the script from a Bash shell with Docker Desktop and Compose | Do not assume Apple Metal GPU passthrough to the Ollama Linux container; the default Docker setup runs without that acceleration |

Windows PowerShell is **not** a supported direct entry point for the Bash installer. Use WSL2; a native Windows workflow has not been implemented. On macOS, native Ollama outside Docker may use Apple Silicon GPU acceleration, but that is a different architecture and is **not** wired into the current L-ai Compose stack. These are setup paths, not a claim of end-to-end certification on all machines.

## Default mode (CPU-compatible)

Set `L_AI_GPU=none` (or leave it unset), then run:

```bash
bash scripts/setup.sh
docker compose -f compose.yaml ps
```

The Ollama API remains private on the Compose network, and the Open WebUI port remains bound to loopback.

## Optional NVIDIA GPU

Install compatible GPU drivers and configure the NVIDIA Container Toolkit for Docker on a supported Linux host. Windows GPU passthrough requires the WSL2 backend and compatible NVIDIA drivers. Verify GPU access to Docker **before** enabling the overlay.

Set in `.env`:

```dotenv
L_AI_GPU=nvidia
```

Then run:

```bash
bash scripts/setup.sh
docker compose -f compose.yaml -f compose.gpu.nvidia.yaml config --quiet
docker compose -f compose.yaml -f compose.gpu.nvidia.yaml exec ollama ollama ps
```

The overlay reserves NVIDIA GPU devices for Ollama only; Open WebUI remains unchanged. To issue manual Compose commands with this backend, use `docker compose -f compose.yaml -f compose.gpu.nvidia.yaml ...` or export an equivalent `COMPOSE_FILE`. A successful Compose validation checks YAML structure, **not** that the host GPU is usable.

## Optional AMD GPU (ROCm on Linux)

This option requires a supported AMD GPU, ROCm-compatible Linux drivers, and available `/dev/kfd` and `/dev/dri` device nodes. It switches the Ollama image to `ollama/ollama:rocm` and passes through those devices. It is not intended for Windows/WSL2 or macOS by default.

```dotenv
L_AI_GPU=amd
```

```bash
bash scripts/setup.sh
docker compose -f compose.yaml -f compose.gpu.amd.yaml config --quiet
docker compose -f compose.yaml -f compose.gpu.amd.yaml exec ollama ollama ps
```

Check the GPU's actual usage with host diagnostics and Ollama logs while running inference. The `ollama ps` command does not itself guarantee GPU acceleration.

## Switching between backends

Change `L_AI_GPU` in `.env` and rerun `bash scripts/setup.sh`. Compose may recreate the Ollama container but the named Ollama and Open WebUI volumes are preserved. Avoid `docker compose down -v`.

For backend-preserving upgrades and routine Compose commands, see [operations and upgrades](reliability.md#operations-and-upgrades). For memory and model choices, see [model configuration](model-configuration.md).

## Upstream documentation

- [Docker Compose GPU support](https://docs.docker.com/compose/how-tos/gpu-support/)
- [Ollama Docker and GPU setup](https://github.com/ollama/ollama/blob/main/docs/docker.mdx)
- [Docker Desktop for Windows GPU support](https://docs.docker.com/desktop/features/gpu)
