"""Validate that the shipped assistant is generic and consistently named."""
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]


class GeneralPurposeTests(unittest.TestCase):
    def test_model_has_general_purpose_instructions(self):
        modelfile = (ROOT / "config/Modelfile").read_text(encoding="utf-8")
        self.assertIn("FROM qwen3:4b-instruct", modelfile)
        self.assertIn("propósito geral", modelfile)
        self.assertIn("base RAG", modelfile)
        self.assertIn("Não invente referências", modelfile)

    def test_setup_creates_lai(self):
        setup = (ROOT / "scripts/setup.sh").read_text(encoding="utf-8")
        self.assertIn("ollama create lai -f /config/Modelfile", setup)

    def test_docs_use_current_assistant(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        guide = (ROOT / "docs/knowledge-pipeline.md").read_text(encoding="utf-8")
        self.assertRegex(readme, r"(?<![A-Za-z])lai(?![A-Za-z])")
        self.assertRegex(guide, r"(?<![A-Za-z])lai(?![A-Za-z])")
        self.assertNotIn("Migração de instalações anteriores", readme)

    def test_default_prompt_is_not_domain_restricted(self):
        modelfile = (ROOT / "config/Modelfile").read_text(encoding="utf-8")
        self.assertIn("pesquisa, estudo, programação, escrita", modelfile)
        self.assertIn("perguntas pertinentes", modelfile)


if __name__ == "__main__":
    unittest.main()
