import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from mdman.cli import app, read_source
from mdman.markdown import add_toc, extract_headings, github_heading_id
from mdman.renderer import _less_raw_control_codes


class CliTest(unittest.TestCase):
    runner = CliRunner()

    def test_reads_utf8_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            filename = Path(directory) / "beispiel.md"
            filename.write_text("# Überschrift\n", encoding="utf-8")

            self.assertEqual(
                read_source(str(filename)),
                "# Überschrift\n",
            )

    def test_reads_stdin(self) -> None:
        with patch("sys.stdin.read", return_value="# stdin\n"):
            self.assertEqual(read_source("-"), "# stdin\n")

    def test_reports_missing_file(self) -> None:
        result = self.runner.invoke(app, ["does-not-exist.md"])

        self.assertEqual(result.exit_code, 1)
        self.assertIn("mdman:", result.output)

    def test_renders_markdown_without_colour(self) -> None:
        result = self.runner.invoke(
            app, ["-"], input="# Titel\n\nText\n"
        )

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

    def test_duplicate_heading_ids(self) -> None:
        source = (
            "# Über uns\n\n```\n## Kein Eintrag\n```\n"
            "\n## Über uns\n"
        )

        self.assertEqual(
            extract_headings(source),
            [("Über uns", "über-uns"), ("Über uns", "über-uns-1")],
        )

    def test_adds_toc_before_markdown(self) -> None:
        result = self.runner.invoke(
            app, ["--toc", "-"], input="# Titel\n\nText\n"
        )

        self.assertEqual(result.exit_code, 0)
        self.assertIn("Inhaltsverzeichnis", result.output)
        self.assertLess(
            result.output.index("Inhaltsverzeichnis"),
            result.output.index("Titel"),
        )
        self.assertIn("#titel", add_toc("# Titel\n"))

    def test_toc_preserves_heading_hierarchy(self) -> None:
        source = (
            "# Kapitel\n\n## Abschnitt\n\n### Detail\n"
            "\n# Schluss\n"
        )

        toc = add_toc(source)

        expected = (
            "- [Kapitel](#kapitel)\n"
            "  - [Abschnitt](#abschnitt)\n"
            "    - [Detail](#detail)\n"
            "- [Schluss](#schluss)"
        )
        self.assertIn(expected, toc)

    def test_github_heading_id_rules(self) -> None:
        """Behält Unicode bei und behandelt Leerraum wie GitHub."""
        self.assertEqual(github_heading_id("A  B"), "a--b")
        self.assertEqual(github_heading_id("A\tB"), "ab")
        self.assertEqual(github_heading_id("Über Θ! uns"), "über-θ-uns")

    def test_empty_heading_after_markup_is_skipped(self) -> None:
        self.assertEqual(extract_headings("# **~~**\n"), [])

    def test_markdown_output(self) -> None:
        """Gibt verarbeitetes Markdown direkt auf stdout aus."""
        result = self.runner.invoke(
            app,
            ["--format", "markdown", "--toc", "-"],
            input="# Titel\n",
        )

        self.assertEqual(result.exit_code, 0)
        self.assertIn("**Inhaltsverzeichnis**", result.output)
        self.assertIn("- [Titel](#titel)", result.output)

    def test_markdown_format_rejects_pager(self) -> None:
        result = self.runner.invoke(
            app,
            ["--format", "markdown", "--pager", "-"],
            input="# Titel\n",
        )

        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("--pager", result.output)

    def test_less_restores_environment(self) -> None:
        with patch.dict(
            os.environ, {"PAGER": "less", "LESS": "-F"}, clear=False
        ):
            with _less_raw_control_codes():
                self.assertEqual(os.environ["LESS"], "-F -R")
            self.assertEqual(os.environ["LESS"], "-F")

    def test_less_option_is_not_duplicated(self) -> None:
        with patch.dict(
            os.environ, {"PAGER": "less", "LESS": "-R -F"}, clear=False
        ):
            with _less_raw_control_codes():
                self.assertEqual(os.environ["LESS"], "-R -F")


if __name__ == "__main__":
    unittest.main()
