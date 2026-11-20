"""Start und Wiederverwendung des lokalen Vite-Editors."""

from __future__ import annotations

import errno
import json
import os
import shutil
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from pathlib import Path
from typing import Annotated

import typer


def edit(
    filename: Annotated[
        Path,
        typer.Argument(
            help="Einzelne Markdown-Datei.", metavar="DATEI"
        ),
    ],
    port: Annotated[
        int,
        typer.Option(
            min=1, max=65535, help="Port des lokalen Editors."
        ),
    ] = 5173,
    open_browser: Annotated[
        bool, typer.Option("--open/--no-open", help="Browser öffnen.")
    ] = False,
) -> None:
    """Markdown-Editor starten; mit --open den Browser öffnen."""
    try:
        launch_editor(filename, port=port, open_browser=open_browser)
    except (OSError, ValueError) as error:
        typer.echo(f"mdman: {error}", err=True)
        raise typer.Exit(1) from error


def launch_editor(
    filename: Path, *, port: int, open_browser: bool
) -> None:
    filename = filename.resolve(strict=True)
    if not filename.is_file() or filename.suffix.lower() not in {
        ".md",
        ".markdown",
    }:
        raise ValueError("Bitte eine einzelne Markdown-Datei angeben.")
    base = f"http://127.0.0.1:{port}"
    url = f"{base}/?{urllib.parse.urlencode({'file': str(filename)})}"
    if editor_is_running(base):
        typer.echo(url)
        if open_browser:
            webbrowser.open(url)
        return

    project = Path(__file__).resolve().parents[2] / "editor"
    entry = project / "bin" / "serve.mjs"
    if (
        not entry.is_file()
        or not (project / "node_modules/vite").is_dir()
    ):
        raise ValueError(
            "Browser-Editor fehlt. Im mdman-Repo make setup ausführen."
        )
    node = shutil.which("node")
    if node is None:
        raise ValueError(
            "Node.js fehlt. Benötigt wird Node.js >= 22.12."
        )
    args = [
        node,
        str(entry),
        "--file",
        str(filename),
        "--port",
        str(port),
    ]
    if open_browser:
        args.append("--open")
    typer.echo(f"Editor: {url}\nBeenden mit Strg+C.")
    os.execvpe(node, args, os.environ.copy())


def editor_is_running(base: str) -> bool:
    request = urllib.request.Request(f"{base}/api/status")
    try:
        with urllib.request.urlopen(request, timeout=1) as response:
            status = json.loads(response.read(1024))
    except urllib.error.HTTPError as error:
        raise ValueError(
            "Port ist durch einen anderen Server belegt."
        ) from error
    except urllib.error.URLError as error:
        if (
            isinstance(error.reason, OSError)
            and error.reason.errno == errno.ECONNREFUSED
        ):
            return False
        raise ValueError(
            "Lokaler Editor ist nicht erreichbar."
        ) from error
    except (TimeoutError, json.JSONDecodeError) as error:
        raise ValueError(
            "Port antwortet nicht als mdman-Editor."
        ) from error
    if status != {"application": "mdman-editor", "protocol": 1}:
        raise ValueError("Port ist durch einen anderen Server belegt.")
    return True
