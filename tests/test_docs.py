"""Keep local Markdown CLI examples and links aligned with the actual parser."""
import re
import shlex
import unittest
from pathlib import Path
from ingest.cli import parse_args

ROOT = Path(__file__).resolve().parents[1]
FILES = [ROOT / "README.md", *sorted((ROOT / "docs").glob("*.md"))]


def cli_examples(markdown):
    # Only executable command blocks, never prose or a literal urls.txt example.
    for block in re.findall(r"```(?:bash|sh)\n(.*?)\n```", markdown, flags=re.S):
        lines = block.replace("\\\n", " ").splitlines()
        for line in lines:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if " -m ingest.cli " not in " " + line + " ":
                continue
            argv = shlex.split(line)
            position = argv.index("ingest.cli")
            yield argv[position + 1:]


class DocumentationTests(unittest.TestCase):
    def test_all_local_markdown_links_exist(self):
        for filename in FILES:
            text = filename.read_text(encoding="utf-8")
            for dest in re.findall(r"(?<!!)\[[^\]]+\]\(([^)]+)\)", text):
                if dest.startswith(("http:", "https:", "mailto:", "#")):
                    continue
                target = dest.split("#", 1)[0]
                with self.subTest(file=str(filename), target=target):
                    self.assertTrue((filename.parent / target).exists())

    def test_commands_are_recognized_by_argparse(self):
        found = 0
        for filename in FILES:
            for argv in cli_examples(filename.read_text(encoding="utf-8")):
                found += 1
                with self.subTest(file=str(filename), argv=argv):
                    args = parse_args(argv)
                    self.assertTrue(args.url or args.urls_file or args.sitemap
                                    or args.remote_pdf or args.file or args.directory)
        self.assertGreaterEqual(found, 9)

    def test_no_old_feature_contradictions(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertNotIn("Não há crawling recursivo", readme)
        self.assertNotIn("Não há OCR nesta etapa", readme)
        self.assertIn("--crawl", readme)
        self.assertIn("--ocr", readme)
        self.assertIn("--sitemap", readme)

    def test_readme_tree_has_real_lines(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        tree = re.search(r"```text\n(.*?)\n```", readme, flags=re.S)
        self.assertIsNotNone(tree)
        self.assertNotIn("\\n", tree.group(1))


if __name__ == "__main__":
    unittest.main()
