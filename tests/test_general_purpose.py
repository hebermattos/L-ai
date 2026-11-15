"""Validate that the shipped assistant is generic and consistently named."""
import pathlib
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]


class GeneralPurposeTests(unittest.TestCase):
    def test_model_has_general_purpose_instructions(self):
        modelfile = (ROOT / "config/Modelfile").read_text(encoding="utf-8")
        self.assertIn("FROM qwen3:4b-instruct", modelfile)
        self.assertIn("general-purpose", modelfile)
        self.assertIn("RAG passages", modelfile)
        self.assertIn("Do not fabricate references", modelfile)

    def test_setup_creates_lai(self):
        setup = (ROOT / "scripts/setup.sh").read_text(encoding="utf-8")
        self.assertIn("ollama create lai -f /config/Modelfile", setup)

    def test_docs_use_current_assistant(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        guide = (ROOT / "docs/knowledge-pipeline.md").read_text(encoding="utf-8")
        self.assertRegex(readme, r"(?<![A-Za-z])lai(?![A-Za-z])")
        self.assertRegex(guide, r"(?<![A-Za-z])lai(?![A-Za-z])")
        self.assertNotIn("Migration from previous installations", readme)

    def test_default_prompt_is_not_domain_restricted(self):
        modelfile = (ROOT / "config/Modelfile").read_text(encoding="utf-8")
        self.assertIn("research, learning, programming, writing", modelfile)
        self.assertIn("relevant questions", modelfile)


if __name__ == "__main__":
    unittest.main()
