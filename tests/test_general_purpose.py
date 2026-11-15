"""The default assistant and public examples must remain domain-neutral."""
import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
FILES = [
    ROOT / "config/Modelfile",
    ROOT / "README.md",
    ROOT / "docs/knowledge-pipeline.md",
    ROOT / "tests/fixtures/retrieval_cases.json",
    ROOT / "tests/test_p1_import.py",
    ROOT / "tests/test_p2_sources.py",
]

class GeneralPurposeTests(unittest.TestCase):
    def test_model_has_general_purpose_instructions(self):
        text = (ROOT / "config/Modelfile").read_text(encoding="utf-8")
        self.assertIn("FROM qwen3:4b-instruct", text)
        self.assertIn("propósito geral", text)
        self.assertIn("base RAG", text)
        self.assertIn("Não invente referências", text)

    def test_setup_creates_generic_assistant(self):
        script = (ROOT / "scripts/setup.sh").read_text(encoding="utf-8")
        self.assertIn("ollama create lai -f /config/Modelfile", script)
        self.assertNotIn("ollama create arcana", script)

    def test_default_content_has_no_subject_specialization(self):
        terms = re.compile(r"ocultismo|esoterismo|hermetismo|alquimia|grim[oó]rios?|goetia|cabala", re.I)
        for path in FILES:
            with self.subTest(file=str(path.relative_to(ROOT))):
                text = path.read_text(encoding="utf-8")
                if path.name == "README.md":
                    text = re.sub(r"## Migração de instalações anteriores.*?(?=\\n## |\\Z)", "", text, flags=re.S)
                self.assertIsNone(terms.search(text))

    def test_document_migration_keeps_existing_data(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn("Migração de instalações anteriores", readme)
        self.assertIn("não apaga", readme)
        self.assertIn("modelo **lai**", readme)

if __name__ == "__main__":
    unittest.main()
