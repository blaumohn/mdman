import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from mdman.cli import app
from mdman.jsonl import Entry, JsonlError, read_entries
from mdman.profiles import (
    ProfileError,
    load_profile,
    parse_profile,
    profile_path,
)


def jsonl(*records: object) -> str:
    return "".join(json.dumps(record) + "\n" for record in records)


class ReadEntriesTest(unittest.TestCase):
    def read(self, source: str, **profile: object) -> list[Entry]:
        return read_entries(source, profile=parse_profile(profile))

    def test_recursive_selection_and_missing_fields(self) -> None:
        entries = self.read(
            jsonl({"message": {"body": "# A", "secret": "omit"}}),
            schema={
                "message": {"body": "markdown"},
                "missing": "string",
            },
        )
        self.assertEqual(entries[0].line, 1)
        self.assertEqual(len(entries[0].fields), 1)
        fields = entries[0].fields[0].children
        self.assertEqual(len(fields), 1)
        self.assertEqual(fields[0].kind, "markdown")
        self.assertEqual(fields[0].value, "# A")

    def test_meta_true_recurses_through_every_value(self) -> None:
        record = {"nested": {"tags": ["x", True, None, {"n": 3}]}}
        entries = self.read(
            jsonl(record, {"text": "Hi"}),
            schema={"text": "markdown"},
            meta=True,
        )
        self.assertTrue(entries[0].metadata)
        self.assertFalse(entries[1].metadata)
        self.assertEqual(entries[1].line, 2)
        tags = entries[0].fields[0].children[0]
        self.assertEqual(tags.kind, "list")
        self.assertEqual(len(tags.children), 4)
        self.assertEqual(tags.children[3].children[0].value, 3)

    def test_meta_schema_and_empty_meta_schema(self) -> None:
        for meta in ({"title": "string"}, {}):
            with self.subTest(meta=meta):
                entries = self.read(
                    jsonl(
                        {"title": "Session", "other": 1}, {"body": "x"}
                    ),
                    schema={"body": "markdown"},
                    meta=meta,
                )
                self.assertTrue(entries[0].metadata)
                self.assertEqual(len(entries[0].fields), len(meta))
                self.assertEqual(entries[1].fields[0].value, "x")

    def test_meta_false_uses_normal_schema_for_first_line(self) -> None:
        entries = self.read(
            jsonl({"body": "x"}),
            schema={"body": "markdown"},
            meta=False,
        )
        self.assertFalse(entries[0].metadata)
        self.assertEqual(entries[0].fields[0].value, "x")

    def test_list_items_use_schema(self) -> None:
        entries = self.read(
            jsonl(
                {"files": [{"name": "a", "extra": 2}, {"name": "b"}]}
            ),
            schema={"files": [{"name": "string"}]},
        )
        items = entries[0].fields[0].children
        self.assertEqual(
            [i.children[0].value for i in items], ["a", "b"]
        )
        self.assertTrue(all(len(i.children) == 1 for i in items))

    def test_reports_nested_type_error_with_line_and_path(self) -> None:
        with self.assertRaisesRegex(
            JsonlError, r'Zeile 2:.*\["files"\]\[0\]\["size"\].*number'
        ):
            self.read(
                jsonl({}, {"files": [{"size": True}]}),
                schema={"files": [{"size": "number"}]},
            )

    def test_rejects_wrong_container_and_leaf_types(self) -> None:
        for schema, value in (
            ({"a": "string"}, "x"),
            (["string"], {}),
            ("markdown", None),
            ("string", 1),
            ("number", "1"),
        ):
            with (
                self.subTest(schema=schema, value=value),
                self.assertRaises(JsonlError),
            ):
                self.read(jsonl({"v": value}), schema={"v": schema})

    def test_dates(self) -> None:
        for value in ("2026-11-19", "2026-11-19T12:30:00Z"):
            entries = self.read(
                jsonl({"d": value}), schema={"d": "date"}
            )
            self.assertEqual(entries[0].fields[0].value, value)
        with self.assertRaisesRegex(JsonlError, "ISO-Datum"):
            self.read(jsonl({"d": "2026-02-30"}), schema={"d": "date"})

    def test_invalid_json_and_non_objects(self) -> None:
        for source in (
            "{}\n{kaputt\n",
            "{}\n\n",
            "{}\n[]\n",
            "{}\nNaN\n",
        ):
            with (
                self.subTest(source=source),
                self.assertRaisesRegex(JsonlError, "Zeile 2"),
            ):
                self.read(source, schema={})

    def test_unicode_line_separators_inside_string(self) -> None:
        value = "vorher\u0085mitte\u2028nachher"
        source = json.dumps({"body": value}, ensure_ascii=False) + "\n"
        entries = self.read(source, schema={"body": "markdown"})
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].fields[0].value, value)

    def test_empty_input(self) -> None:
        self.assertEqual(self.read("", schema={}, meta=True), [])


class ProfileTest(unittest.TestCase):
    def test_rejects_invalid_profiles(self) -> None:
        value: object
        for value in (
            [],
            {},
            {"schema": []},
            {"schema": {}, "meta": 1},
            {"schema": {}, "meta": []},
            {"schema": {"a": "unknown"}},
            {"schema": {"a": []}},
            {"schema": {"a": ["string", "date"]}},
            {"schema": {}, "typo": True},
            {"schema": {"a": None}},
        ):
            with (
                self.subTest(value=value),
                self.assertRaises(ProfileError),
            ):
                parse_profile(value)

    def test_xdg_lookup_precedence(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            user, system = (
                Path(directory) / "user",
                Path(directory) / "sys",
            )
            for root in (user, system):
                target = root / "mdman/schemas/session.json"
                target.parent.mkdir(parents=True)
                target.write_text('{"schema": {}}', encoding="utf-8")
            with patch.dict(
                os.environ,
                {
                    "XDG_CONFIG_HOME": str(user),
                    "XDG_CONFIG_DIRS": str(system),
                },
            ):
                self.assertEqual(
                    profile_path("session"),
                    user / "mdman/schemas/session.json",
                )
                (user / "mdman/schemas/session.json").unlink()
                self.assertEqual(
                    profile_path("session"),
                    system / "mdman/schemas/session.json",
                )
                self.assertEqual(load_profile("session").schema, {})

    def test_xdg_home_default_for_unset_empty_and_relative(
        self,
    ) -> None:
        with patch(
            "pathlib.Path.home", return_value=Path("/home/demo")
        ):
            for value in ("", "relative"):
                with patch.dict(os.environ, {"XDG_CONFIG_HOME": value}):
                    self.assertEqual(
                        profile_path("unique-missing-profile"),
                        Path(
                            "/home/demo/.config/mdman/schemas/unique-missing-profile.json"
                        ),
                    )
            with patch.dict(os.environ, {}, clear=True):
                self.assertEqual(
                    profile_path("unique-missing-profile"),
                    Path(
                        "/home/demo/.config/mdman/schemas/unique-missing-profile.json"
                    ),
                )


class JsonlCliTest(unittest.TestCase):
    runner = CliRunner()

    def test_named_profile_stdin_and_file(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = root / "mdman/schemas/web-sitzung.json"
            config.parent.mkdir(parents=True)
            config.write_text(
                json.dumps(
                    {
                        "schema": {
                            "message": {"body": "markdown"},
                            "name": "string",
                        },
                        "meta": True,
                    }
                ),
                encoding="utf-8",
            )
            source = jsonl(
                {
                    "project": {"name": "mdman"},
                    "tags": ["CLI", "Markdown"],
                },
                {
                    "message": {"body": "# Titel\n\n- Punkt"},
                    "name": "**plain**",
                    "secret": "UNSELECTED",
                },
            )
            data = root / "session.jsonl"
            data.write_text(source, encoding="utf-8")
            for filename in ([], ["-"], [str(data)]):
                with self.subTest(filename=filename):
                    result = self.runner.invoke(
                        app,
                        ["jsonl", "web-sitzung", *filename],
                        input=source,
                        env={
                            "XDG_CONFIG_HOME": directory,
                            "NO_COLOR": "1",
                        },
                    )
                    self.assertEqual(result.exit_code, 0, result.output)
                    for text in (
                        "Metadaten",
                        "Zeile 2",
                        "project",
                        "mdman",
                        "• CLI",
                        "body · Markdown",
                        "Titel",
                        "**plain**",
                    ):
                        self.assertIn(text, result.output)
                    self.assertIn("│", result.output)
                    self.assertNotIn("# Titel", result.output)
                    self.assertNotIn("UNSELECTED", result.output)
                    self.assertNotIn("\x1b[", result.output)

    def test_profile_errors_and_no_partial_output(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "profile.json"
            for profile in (
                "invalid",
                '{"schema": {"text": "markdown"}}',
            ):
                path.write_text(profile, encoding="utf-8")
                result = self.runner.invoke(
                    app,
                    ["jsonl", str(path)],
                    input=jsonl({"text": "FIRST"}, {"text": 3}),
                )
                self.assertEqual(result.exit_code, 1)
                self.assertIn("mdman:", result.output)
                self.assertNotIn("FIRST", result.output)
            result = self.runner.invoke(
                app, ["jsonl", str(path / "missing")]
            )
            self.assertEqual(result.exit_code, 1)
            self.assertIn("Profil", result.output)

    def test_jsonl_help_and_removed_content_option(self) -> None:
        result = self.runner.invoke(app, ["jsonl", "--help"])
        self.assertEqual(result.exit_code, 0)
        self.assertIn("PROFIL", result.output)
        self.assertNotIn("--content", result.output)
        result = self.runner.invoke(app, ["--content", "text", "-"])
        self.assertEqual(result.exit_code, 2)
