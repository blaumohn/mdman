import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from mdman.cli import app, read_source
from mdman.renderer import extract_headings, markdown_with_toc


class CliTest(unittest.TestCase):
    runner = CliRunner()

    def test_reads_utf8_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            filename = Path(directory) / "beispiel.md"
            filename.write_text("# Überschrift\n", encoding="utf-8")

            self.assertEqual(read_source(str(filename)), "# Überschrift\n")

    def test_reads_stdin(self) -> None:
        with patch("sys.stdin.read", return_value="# stdin\n"):
            self.assertEqual(read_source("-"), "# stdin\n")

    def test_reports_missing_file(self) -> None:
        result = self.runner.invoke(app, ["does-not-exist.md"])

        self.assertEqual(result.exit_code, 1)
        self.assertIn("mdman:", result.output)

    def test_renders_markdown_without_colour(self) -> None:
        result = self.runner.invoke(app, ["-"], input="# Titel\n\nText\n")

        self.assertEqual(result.exit_code, 0)
        self.assertIn("Titel", result.output)
        self.assertNotIn("\x1b[", result.output)

    def test_renders_gfm_table(self) -> None:
        source = "| Name | Wert |\n| --- | ---: |\n| alpha | 1 |\n"
        result = self.runner.invoke(app, ["-"], input=source)

        self.assertEqual(result.exit_code, 0)
        self.assertIn("Name", result.output)
        self.assertIn("alpha", result.output)
        self.assertIn("1", result.output)

    def test_extracts_headings_and_makes_duplicate_slugs_unique(self) -> None:
        source = "# Über uns\n\n```\n## Kein Eintrag\n```\n\n## Über uns\n"

        self.assertEqual(
            extract_headings(source),
            [("Über uns", "uber-uns"), ("Über uns", "uber-uns-1")],
        )

    def test_adds_toc_before_markdown(self) -> None:
        result = self.runner.invoke(app, ["--with-toc", "-"], input="# Titel\n\nText\n")

        self.assertEqual(result.exit_code, 0)
        self.assertIn("Inhaltsverzeichnis", result.output)
        self.assertLess(result.output.index("Inhaltsverzeichnis"), result.output.index("Titel"))
        self.assertIn("#titel", markdown_with_toc("# Titel\n"))


if __name__ == "__main__":
    unittest.main()
