from __future__ import annotations

import errno
import io
import json
import subprocess
import sys
import urllib.error
from pathlib import Path
from unittest.mock import patch

import pytest
from typer.testing import CliRunner

from mdman.cli import app
from mdman.editor import editor_is_running, launch_editor


def test_reuses_running_editor_for_file_in_another_directory(
    tmp_path: Path,
) -> None:
    document = tmp_path / "docs" / "mit platz.md"
    document.parent.mkdir()
    document.write_text("# Titel\n", encoding="utf8")
    with (
        patch("mdman.editor.editor_is_running", return_value=True),
        patch("mdman.editor.webbrowser.open") as browser,
        patch("mdman.editor.os.execvpe") as execute,
    ):
        launch_editor(document, port=5173, open_browser=True)
    assert browser.call_args.args[0].startswith(
        "http://127.0.0.1:5173/?file="
    )
    assert "mit+platz.md" in browser.call_args.args[0]
    execute.assert_not_called()


def test_no_open_prints_url_without_opening_browser(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    document = tmp_path / "test.md"
    document.write_text("# Titel", encoding="utf8")
    with (
        patch("mdman.editor.editor_is_running", return_value=True),
        patch("mdman.editor.webbrowser.open") as browser,
    ):
        launch_editor(document, port=5174, open_browser=False)
    browser.assert_not_called()
    assert "http://127.0.0.1:5174/" in capsys.readouterr().out


def test_directory_is_not_a_document(tmp_path: Path) -> None:
    result = CliRunner().invoke(app, ["edit", str(tmp_path)])
    assert result.exit_code == 1
    assert "einzelne Markdown-Datei" in result.output


def test_missing_file_is_reported(tmp_path: Path) -> None:
    result = CliRunner().invoke(
        app, ["edit", str(tmp_path / "fehlt.md")]
    )
    assert result.exit_code == 1
    assert "mdman:" in result.output


def test_status_identifies_mdman() -> None:
    response = io.BytesIO(
        json.dumps(
            {"application": "mdman-editor", "protocol": 1}
        ).encode()
    )
    with patch("urllib.request.urlopen", return_value=response):
        assert editor_is_running("http://127.0.0.1:5173")


def test_other_service_is_not_reused() -> None:
    with (
        patch("urllib.request.urlopen", return_value=io.BytesIO(b"{}")),
        pytest.raises(ValueError, match="anderen Server"),
    ):
        editor_is_running("http://127.0.0.1:5173")


def test_connection_refused_means_no_running_editor() -> None:
    error = urllib.error.URLError(
        OSError(errno.ECONNREFUSED, "refused")
    )
    with patch("urllib.request.urlopen", side_effect=error):
        assert not editor_is_running("http://127.0.0.1:5173")


def test_timeout_is_not_treated_as_missing_server() -> None:
    with (
        patch("urllib.request.urlopen", side_effect=TimeoutError()),
        pytest.raises(ValueError, match="antwortet nicht"),
    ):
        editor_is_running("http://127.0.0.1:5173")


def test_public_entry_point_exposes_editor_help() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "mdman", "edit", "--help"],
        capture_output=True,
        text=True,
        check=False,
        timeout=10,
    )
    assert result.returncode == 0
    assert "DATEI" in result.stdout


def test_top_level_help_lists_edit_and_render() -> None:
    result = CliRunner().invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "edit" in result.output
    assert "render" in result.output
