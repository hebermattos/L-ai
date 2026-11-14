import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]


class ProjectConfigurationTests(unittest.TestCase):
    def test_required_files_exist(self):
        for path in [
            "compose.yaml",
            ".env.example",
            "config/Modelfile",
            "scripts/setup.sh",
            "scripts/check.sh",
        ]:
            with self.subTest(path=path):
                self.assertTrue((ROOT / path).is_file())

    def test_ollama_internal_only(self):
        compose = (ROOT / "compose.yaml").read_text(encoding="utf-8")
        ollama_section = compose.split("  ollama:", 1)[1].split("  open-webui:", 1)[0]
        self.assertNotIn("ports:", ollama_section)
        self.assertIn("http://ollama:11434", compose)
        self.assertIn("127.0.0.1:3000:8080", compose)

    def test_webui_requires_a_secret(self):
        compose = (ROOT / "compose.yaml").read_text(encoding="utf-8")
        self.assertIn("WEBUI_SECRET_KEY: ${WEBUI_SECRET_KEY:?", compose)

    def test_document_library_ignored(self):
        ignored = (ROOT / ".gitignore").read_text(encoding="utf-8")
        self.assertIn("biblioteca/**", ignored)
        self.assertIn(".env", ignored)

    def test_model_is_instruction_quantized(self):
        modelfile = (ROOT / "config/Modelfile").read_text(encoding="utf-8")
        self.assertIn("FROM qwen3:4b-instruct", modelfile)
        self.assertIn("PARAMETER num_ctx 8192", modelfile)

    def test_setup_creates_secret_and_model(self):
        setup = (ROOT / "scripts/setup.sh").read_text(encoding="utf-8")
        self.assertIn("openssl rand -hex 32", setup)
        self.assertIn("ollama create arcana", setup)


if __name__ == "__main__":
    unittest.main()
