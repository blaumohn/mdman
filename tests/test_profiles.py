import copy
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from jsonschema import Draft202012Validator
from typer.testing import CliRunner

from mdman.cli import app
from mdman.profile_commands import profile_help
from mdman.profiles import (
    PROFILE_SCHEMA,
    ProfileError,
    parse_profile,
    profile_directories,
)


class ProfileCommandsTest(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.user = self.root / "user"
        self.system = self.root / "system"
        environment = patch.dict(
            os.environ,
            {
                "XDG_CONFIG_HOME": str(self.user),
                "XDG_CONFIG_DIRS": str(self.system),
                "NO_COLOR": "1",
            },
        )
        environment.start()
        self.addCleanup(environment.stop)
        self.runner = CliRunner()

    def write_profile(
        self,
        root: Path,
        name: str,
        value: object,
    ) -> Path:
        path = root / "mdman" / "schemas" / f"{name}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value), encoding="utf-8")
        return path

    def test_list_shows_empty_directories_without_creating_them(
        self,
    ) -> None:
        result = self.runner.invoke(app, ["profiles", "list"])
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn(str(self.user / "mdman/schemas"), result.output)
        self.assertIn(str(self.system / "mdman/schemas"), result.output)
        self.assertIn("Keine Profile", result.output)
        self.assertFalse(self.user.exists())
        self.assertFalse(self.system.exists())

    def test_list_marks_shadowed_profiles(self) -> None:
        user = self.write_profile(self.user, "session", {"schema": {}})
        system = self.write_profile(
            self.system, "session", {"schema": {}}
        )
        self.write_profile(self.system, "broken", {"schema": "wrong"})
        result = self.runner.invoke(
            app,
            ["profiles", "list"],
            terminal_width=180,
        )
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn(str(user), result.output)
        self.assertIn(str(system), result.output)
        self.assertIn("überlagert", result.output)
        self.assertIn("broken", result.output)
        self.assertLess(
            result.output.index(str(user)),
            result.output.index(str(system)),
        )

    def test_validate_all_reports_errors_and_continues(self) -> None:
        invalid = self.write_profile(
            self.user,
            "a-bad",
            {
                "schema": {"message": {"body": "markdon"}},
            },
        )
        valid = self.write_profile(self.user, "z-good", {"schema": {}})
        result = self.runner.invoke(app, ["profiles", "validate"])
        self.assertEqual(result.exit_code, 1, result.output)
        # Rich may wrap paths, so compare after removing whitespace.
        compact = "".join(result.output.split())
        self.assertIn(str(invalid), compact)
        self.assertIn(str(valid), compact)
        self.assertIn("✗", result.output)
        self.assertIn("✓", result.output)
        self.assertIn('["message"]["body"]', result.output)

    def test_validate_name_uses_active_profile_and_all_checks_shadowed(
        self,
    ) -> None:
        self.write_profile(
            self.user, "session", {"schema": {}, "meta": True}
        )
        self.write_profile(self.system, "session", {"schema": None})
        selected = self.runner.invoke(
            app, ["profiles", "validate", "session"]
        )
        self.assertEqual(selected.exit_code, 0, selected.output)
        all_files = self.runner.invoke(app, ["profiles", "validate"])
        self.assertEqual(all_files.exit_code, 1, all_files.output)

    def test_validate_explicit_path_and_bad_json(self) -> None:
        path = self.root / "outside.json"
        path.write_text('{"schema": {}, "meta": {}}', encoding="utf-8")
        result = self.runner.invoke(
            app, ["profiles", "validate", str(path)]
        )
        self.assertEqual(result.exit_code, 0, result.output)
        path.write_text("{broken", encoding="utf-8")
        result = self.runner.invoke(
            app, ["profiles", "validate", str(path)]
        )
        self.assertEqual(result.exit_code, 1, result.output)
        self.assertIn("✗", result.output)

    def test_validate_missing_and_empty(self) -> None:
        result = self.runner.invoke(app, ["profiles", "validate"])
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn("Keine Profile", result.output)
        result = self.runner.invoke(
            app, ["profiles", "validate", "missing"]
        )
        self.assertEqual(result.exit_code, 1, result.output)
        self.assertIn("missing.json", result.output)

    def test_schema_output_is_plain_json_and_valid_schema(self) -> None:
        result = self.runner.invoke(app, ["profiles", "schema"])
        self.assertEqual(result.exit_code, 0, result.output)
        schema = json.loads(result.output)
        self.assertEqual(schema, PROFILE_SCHEMA)
        Draft202012Validator.check_schema(schema)
        validator = Draft202012Validator(schema)
        for example in schema["examples"]:
            validator.validate(example)
            parse_profile(example)

    def test_help_contains_schema_descriptions_and_examples(
        self,
    ) -> None:
        for command in ("jsonl", "profiles"):
            with self.subTest(command=command):
                result = self.runner.invoke(app, [command, "--help"])
                self.assertEqual(result.exit_code, 0, result.output)
                for text in (
                    "meta: true",
                    "meta: false",
                    "meta: {...}",
                    "markdown",
                    "XDG_CONFIG_HOME",
                    "profiles schema",
                ):
                    self.assertIn(text, result.output)
                lines = [
                    line.strip() for line in result.output.splitlines()
                ]
                self.assertIn('"meta": true', lines)
                self.assertIn('"description": "markdown"', lines)
                self.assertIn("{", lines)
                self.assertTrue(
                    any(line.startswith("Objekte —") for line in lines),
                    result.output,
                )
                self.assertNotIn("```", result.output)

    def test_schema_changes_feed_help_and_validation(self) -> None:
        schema = copy.deepcopy(PROFILE_SCHEMA)
        schema["properties"]["meta"]["description"] = "NEUE ERKLÄRUNG"
        schema["$defs"]["leaf"]["oneOf"].append(
            {
                "const": "future-type",
                "title": "future-type",
                "description": "NEUER TYP",
            }
        )
        validator = Draft202012Validator(schema)
        with (
            patch("mdman.profile_commands.PROFILE_SCHEMA", schema),
            patch("mdman.profiles.PROFILE_VALIDATOR", validator),
        ):
            help_text = profile_help()
            self.assertIn("NEUE ERKLÄRUNG", help_text)
            self.assertIn("future-type", help_text)
            self.assertIn("NEUER TYP", help_text)
            parse_profile({"schema": {"body": "future-type"}})
        with self.assertRaises(ProfileError):
            parse_profile({"schema": {"body": "future-type"}})

    def test_profile_search_directories_deduplicate_and_skip_relative(
        self,
    ) -> None:
        with patch.dict(
            os.environ,
            {
                "XDG_CONFIG_DIRS": os.pathsep.join(
                    [
                        str(self.user),
                        "relative",
                        str(self.system),
                        str(self.system),
                    ]
                ),
            },
        ):
            self.assertEqual(
                profile_directories(),
                [
                    self.user / "mdman/schemas",
                    self.system / "mdman/schemas",
                ],
            )
