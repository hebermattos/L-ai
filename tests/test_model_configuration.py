"""Exercise setup configuration with a fake Docker command, without downloading models."""

import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ConfigurableModelSetupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / "scripts").mkdir()
        (self.root / "config").mkdir()
        shutil.copyfile(ROOT / "scripts/setup.sh", self.root / "scripts/setup.sh")
        shutil.copyfile(ROOT / "config/Modelfile", self.root / "config/Modelfile")
        self.bin_dir = self.root / "bin"
        self.bin_dir.mkdir()
        docker = self.bin_dir / "docker"
        docker.write_text(
            "#!/usr/bin/env bash\n"
            "printf '%s\\n' \"COMPOSE_FILE=${COMPOSE_FILE:-}\" >> \"$FAKE_DOCKER_LOG\"\n"
            "printf '%s\\n' \"$*\" >> \"$FAKE_DOCKER_LOG\"\n"
            "if [[ \"$*\" == *' sh -c '* ]]; then\n"
            "  cat > \"$FAKE_MODELFILE\"\n"
            "fi\n", encoding="utf-8")
        docker.chmod(0o755)
        (self.root / ".env").write_text(
            "WEBUI_SECRET_KEY=test-only-generated-secret\n", encoding="utf-8")
        self.log = self.root / "docker.log"
        self.generated = self.root / "rendered.Modelfile"

    def execute(self, overrides=None):
        env = os.environ.copy()
        for key in ("L_AI_MODEL", "L_AI_CONTEXT_LENGTH", "OLLAMA_NUM_PARALLEL",
                    "OLLAMA_MAX_LOADED_MODELS", "L_AI_GPU", "COMPOSE_FILE"):
            env.pop(key, None)
        env.update({
            "PATH": f"{self.bin_dir}:{env['PATH']}",
            "FAKE_DOCKER_LOG": str(self.log),
            "FAKE_MODELFILE": str(self.generated),
        })
        env.update(overrides or {})
        return subprocess.run(
            ["bash", str(self.root / "scripts/setup.sh")],
            env=env, text=True, capture_output=True, check=False,
        )

    def test_backward_compatible_defaults(self):
        result = self.execute()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("FROM qwen3:4b-instruct", self.generated.read_text())
        self.assertIn("PARAMETER num_ctx 8192", self.generated.read_text())
        self.assertIn("ollama pull qwen3:4b-instruct", self.log.read_text())
        self.assertEqual(
            (ROOT / "config/Modelfile").read_text(),
            (self.root / "config/Modelfile").read_text(),
        )

    def test_env_file_model_and_context(self):
        with (self.root / ".env").open("a", encoding="utf-8") as stream:
            stream.write("L_AI_MODEL=llama3.2:3b\nL_AI_CONTEXT_LENGTH=4096\n")
        result = self.execute()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("FROM llama3.2:3b", self.generated.read_text())
        self.assertIn("PARAMETER num_ctx 4096", self.generated.read_text())
        self.assertIn("ollama pull llama3.2:3b", self.log.read_text())

    def test_process_environment_takes_precedence(self):
        with (self.root / ".env").open("a", encoding="utf-8") as stream:
            stream.write("L_AI_MODEL=qwen3:4b-instruct\n")
        result = self.execute({"L_AI_MODEL": "gemma3:4b"})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("FROM gemma3:4b", self.generated.read_text())

    def test_nvidia_backend_uses_gpu_overlay(self):
        result = self.execute({"L_AI_GPU": "nvidia"})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("COMPOSE_FILE=compose.yaml:compose.gpu.nvidia.yaml", self.log.read_text())

    def test_amd_backend_uses_rocm_overlay(self):
        result = self.execute({"L_AI_GPU": "amd"})
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("COMPOSE_FILE=compose.yaml:compose.gpu.amd.yaml", self.log.read_text())

    def test_env_file_backend_selection(self):
        with (self.root / ".env").open("a", encoding="utf-8") as stream:
            stream.write("L_AI_GPU=nvidia\\n")
        result = self.execute()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("COMPOSE_FILE=compose.yaml:compose.gpu.nvidia.yaml", self.log.read_text())

    def test_rejects_invalid_settings_before_docker_start(self):
        for overrides in (
            {"L_AI_MODEL": "model;unexpected"},
            {"L_AI_CONTEXT_LENGTH": "0"},
            {"OLLAMA_NUM_PARALLEL": "-1"},
            {"OLLAMA_MAX_LOADED_MODELS": "two"},
            {"L_AI_GPU": "not-a-backend"},
        ):
            with self.subTest(overrides=overrides):
                self.log.unlink(missing_ok=True)
                result = self.execute(overrides)
                self.assertNotEqual(result.returncode, 0)
                if self.log.exists():
                    self.assertNotIn("compose up -d", self.log.read_text())


if __name__ == "__main__":
    unittest.main()
