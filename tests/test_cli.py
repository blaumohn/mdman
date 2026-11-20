import os
import stat
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from mdman.cli import app, read_source
from mdman.markdown import (
    TOC_END_MARKER,
    TOC_START_MARKER,
    add_toc,
    extract_headings,
    github_heading_id,
)
from mdman.renderer import _less_raw_control_codes, render_markdown


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

    def test_hides_citation_markers_in_markdown_prose(self) -> None:
        source = (
            "**שלום**\ue200cite<U+E202>turn2search0"
            "\ue202turn2view1<U+E201>.\n\n"
            "א<U+E200>ב<U+E201>ג<U+E202>ד\ue200ה\ue201ו\ue202.\n\n"
            "`<U+E200>` und <U+E203>\n"
        )
        result = self.runner.invoke(app, ["-"], input=source)
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertEqual(
            [
                line.strip()
                for line in result.output.splitlines()
                if line.strip()
            ],
            ["שלום.", "אבגדהו.", "<U+E200> und <U+E203>"],
        )
        exported = self.runner.invoke(
            app, ["--format", "markdown", "-"], input=source
        )
        self.assertEqual(exported.exit_code, 0, exported.output)
        self.assertEqual(exported.output, source)

    def test_renders_gfm_table(self) -> None:
        source = "| Name | Wert |\n| --- | ---: |\n| alpha | 1 |\n"
        result = self.runner.invoke(app, ["-"], input=source)

        self.assertEqual(result.exit_code, 0)
        self.assertIn("Name", result.output)
        self.assertIn("alpha", result.output)
        self.assertIn("1", result.output)

    def test_duplicate_heading_ids(self) -> None:
        source = (
            "# Über uns\n\n```\n## Kein Eintrag\n```\n\n## Über uns\n"
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
        self.assertNotIn("Inhaltsverzeichnis", result.output)
        toc = add_toc("# Titel\n")
        self.assertTrue(toc.startswith("- [Titel](#titel)"))

    def test_toc_preserves_heading_hierarchy(self) -> None:
        source = (
            "# Kapitel\n\n## Abschnitt\n\n### Detail\n\n# Schluss\n"
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

    def test_github_heading_id_keeps_hyphen_and_underscore(
        self,
    ) -> None:
        """Bindestrich und Unterstrich bleiben, Gedankenstrich nicht."""
        self.assertEqual(
            github_heading_id("7. Repository-Aufbau"),
            "7-repository-aufbau",
        )
        self.assertEqual(
            github_heading_id("8. Weg zum ersten Go-live"),
            "8-weg-zum-ersten-go-live",
        )
        self.assertEqual(github_heading_id("snake_case"), "snake_case")
        self.assertEqual(github_heading_id("A – B"), "a--b")

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
        self.assertNotIn("Inhaltsverzeichnis", result.output)
        self.assertIn("- [Titel](#titel)", result.output)

    def test_markdown_output_uses_existing_toc_markers(self) -> None:
        source = (
            "# Seite\n\n"
            f"{TOC_START_MARKER}\n"
            f"{TOC_END_MARKER}\n\n"
            "## Abschnitt\n"
        )

        result = self.runner.invoke(
            app,
            ["--format", "markdown", "--toc", "-"],
            input=source,
        )

        self.assertEqual(result.exit_code, 0)
        self.assertNotIn("- [Seite](#seite)", result.output)
        self.assertIn("- [Abschnitt](#abschnitt)", result.output)

    def test_toc_markers_at_document_start(self) -> None:
        source = f"{TOC_START_MARKER}\n{TOC_END_MARKER}\n\n# Titel\n"

        toc = add_toc(source)

        self.assertTrue(toc.startswith(f"{TOC_START_MARKER}\n"))
        self.assertEqual(toc.count(TOC_START_MARKER), 1)
        self.assertEqual(toc.count(TOC_END_MARKER), 1)
        self.assertIn("- [Titel](#titel)", toc)

    def test_toc_markers_between_content_blocks(self) -> None:
        source = (
            "# Seite\n\n"
            "Einleitung.\n\n"
            f"{TOC_START_MARKER}\n"
            f"{TOC_END_MARKER}\n\n"
            "Zwischentext.\n\n"
            "## Abschnitt\n"
        )

        toc = add_toc(source)

        self.assertNotIn("- [Seite](#seite)", toc)
        self.assertIn("- [Abschnitt](#abschnitt)", toc)

    def test_toc_hierarchy_starts_after_end_marker(self) -> None:
        source = (
            "# Seite\n\n"
            "## Navigation\n\n"
            f"{TOC_START_MARKER}\n"
            f"{TOC_END_MARKER}\n\n"
            "### Erster Abschnitt\n\n"
            "#### Detail\n"
        )

        toc = add_toc(source)

        self.assertNotIn("- [Seite](#seite)", toc)
        self.assertNotIn("- [Navigation](#navigation)", toc)
        self.assertIn(
            "- [Erster Abschnitt](#erster-abschnitt)\n"
            "  - [Detail](#detail)",
            toc,
        )

    def test_markdown_format_rejects_pager(self) -> None:
        result = self.runner.invoke(
            app,
            ["--format", "markdown", "--pager", "-"],
            input="# Titel\n",
        )

        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("--pager", result.output)

    def test_in_place_adds_marked_toc(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            filename = Path(directory) / "beispiel.md"
            filename.write_text("# Titel\n", encoding="utf-8")

            result = self.runner.invoke(
                app, ["--toc", "-i", str(filename)]
            )

            self.assertEqual(result.exit_code, 0)
            written = filename.read_text(encoding="utf-8")
            self.assertIn(TOC_START_MARKER, written)
            self.assertIn("- [Titel](#titel)", written)
            self.assertEqual(written.count(TOC_START_MARKER), 1)

    def test_in_place_replaces_existing_toc(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            filename = Path(directory) / "beispiel.md"
            filename.write_text("# Alt\n", encoding="utf-8")

            self.runner.invoke(app, ["--toc", "-i", str(filename)])
            filename.write_text(
                filename.read_text(encoding="utf-8").replace(
                    "# Alt", "# Neu"
                ),
                encoding="utf-8",
            )
            result = self.runner.invoke(
                app, ["--toc", "-i", str(filename)]
            )

            self.assertEqual(result.exit_code, 0)
            written = filename.read_text(encoding="utf-8")
            self.assertEqual(written.count(TOC_START_MARKER), 1)
            self.assertEqual(written.count(TOC_END_MARKER), 1)
            self.assertIn("- [Neu](#neu)", written)
            self.assertNotIn("- [Alt](#alt)", written)

    def test_in_place_writes_toc_between_existing_markers(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            filename = Path(directory) / "beispiel.md"
            filename.write_text(
                "[Navigation](#abschnitt)\n\n"
                f"{TOC_START_MARKER}\n"
                "Alter TOC\n"
                f"{TOC_END_MARKER}\n\n"
                "## Abschnitt\n",
                encoding="utf-8",
            )

            result = self.runner.invoke(
                app, ["--toc", "-i", str(filename)]
            )

            self.assertEqual(result.exit_code, 0)
            written = filename.read_text(encoding="utf-8")
            self.assertLess(
                written.index("[Navigation](#abschnitt)"),
                written.index(TOC_START_MARKER),
            )
            self.assertLess(
                written.index(TOC_START_MARKER),
                written.index("- [Abschnitt](#abschnitt)"),
            )
            self.assertLess(
                written.index("- [Abschnitt](#abschnitt)"),
                written.index(TOC_END_MARKER),
            )
            self.assertNotIn("Alter TOC", written)

    def test_in_place_toc_ignores_headings_before_markers(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            filename = Path(directory) / "beispiel.md"
            filename.write_text(
                "# Seite\n\n"
                f"{TOC_START_MARKER}\n"
                f"{TOC_END_MARKER}\n\n"
                "## Abschnitt\n\n### Detail\n",
                encoding="utf-8",
            )

            result = self.runner.invoke(
                app, ["--toc", "-i", str(filename)]
            )

            self.assertEqual(result.exit_code, 0)
            written = filename.read_text(encoding="utf-8")
            self.assertNotIn("- [Seite](#seite)", written)
            self.assertIn("- [Abschnitt](#abschnitt)", written)
            self.assertIn("  - [Detail](#detail)", written)

    def test_in_place_clears_toc_without_following_headings(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            filename = Path(directory) / "beispiel.md"
            filename.write_text(
                f"{TOC_START_MARKER}\n"
                "- [Alt](#alt)\n\n---\n"
                f"{TOC_END_MARKER}\n\n"
                "Nur noch Text.\n",
                encoding="utf-8",
            )

            result = self.runner.invoke(
                app, ["--toc", "-i", str(filename)]
            )

            self.assertEqual(result.exit_code, 0)
            written = filename.read_text(encoding="utf-8")
            self.assertNotIn("- [Alt](#alt)", written)
            self.assertIn(TOC_START_MARKER, written)
            self.assertIn(TOC_END_MARKER, written)

    def test_in_place_preserves_file_mode(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            filename = Path(directory) / "beispiel.md"
            filename.write_text("# Titel\n", encoding="utf-8")
            filename.chmod(0o640)

            result = self.runner.invoke(
                app, ["--toc", "-i", str(filename)]
            )

            self.assertEqual(result.exit_code, 0)
            self.assertEqual(
                stat.S_IMODE(filename.stat().st_mode), 0o640
            )

    def test_in_place_rejects_stdin(self) -> None:
        result = self.runner.invoke(app, ["-i", "-"])

        self.assertNotEqual(result.exit_code, 0)

    def test_in_place_requires_toc(self) -> None:
        result = self.runner.invoke(app, ["-i", "README.md"])

        self.assertNotEqual(result.exit_code, 0)

    def test_in_place_rejects_terminal_format(self) -> None:
        result = self.runner.invoke(
            app,
            ["--toc", "-i", "--format", "terminal", "README.md"],
        )

        self.assertNotEqual(result.exit_code, 0)
        self.assertIn("--format", result.output)

    def test_in_place_rejects_pager(self) -> None:
        result = self.runner.invoke(
            app, ["--toc", "-i", "--pager", "README.md"]
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
        with (
            patch.dict(
                os.environ,
                {"PAGER": "less", "LESS": "-R -F"},
                clear=False,
            ),
            _less_raw_control_codes(),
        ):
            self.assertEqual(os.environ["LESS"], "-R -F")

    def test_hebrew_pager_repaints_when_scrolling(self) -> None:
        for source, options in (
            ("שלום **עולם**\n\n" * 40, "-F -R -c -h0 -y0"),
            ("Hello **world**\n\n" * 40, "-F -R"),
        ):
            with (
                self.subTest(source=source[:20]),
                patch.dict(
                    os.environ,
                    {"PAGER": "less", "MANPAGER": "", "LESS": "-F"},
                ),
                patch("mdman.renderer.SystemPager") as pager,
            ):
                seen_options: list[str] = []
                pager.return_value.show.side_effect = (
                    lambda _content, seen=seen_options: seen.append(
                        os.environ["LESS"]
                    )
                )
                render_markdown(source, pager=True)
                self.assertEqual(seen_options, [options])
                self.assertEqual(os.environ["LESS"], "-F")

    def test_less_repaint_restores_unset_environment_on_error(
        self,
    ) -> None:
        with patch.dict(os.environ, {"PAGER": "less", "MANPAGER": ""}):
            os.environ.pop("LESS", None)
            with (
                self.assertRaisesRegex(RuntimeError, "pager failed"),
                _less_raw_control_codes(repaint=True),
            ):
                self.assertEqual(os.environ["LESS"], "-R -c -h0 -y0")
                raise RuntimeError("pager failed")
            self.assertNotIn("LESS", os.environ)

    def test_repaint_does_not_change_other_pagers(self) -> None:
        with (
            patch.dict(
                os.environ,
                {"PAGER": "more", "MANPAGER": "", "LESS": "-F"},
            ),
            _less_raw_control_codes(repaint=True),
        ):
            self.assertEqual(os.environ["LESS"], "-F")


if __name__ == "__main__":
    unittest.main()
