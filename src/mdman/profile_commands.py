from __future__ import annotations

import json
from typing import Annotated, Any

import typer
from rich.console import Console
from rich.table import Table
from rich.text import Text

from mdman.profiles import (
    PROFILE_SCHEMA,
    ProfileError,
    find_profiles,
    load_profile,
    profile_directories,
    profile_path,
)


def describe_schema(node: dict[str, Any]) -> list[str]:
    lines = [f"**{node['title']}** — {node['description']}"]
    if "default" in node:
        lines.append(f"Standard `{json.dumps(node['default'])}`.")
    lines.extend(
        f"- `{variant['title']}` — {variant['description']}"
        for variant in node.get("oneOf", [])
    )
    return lines


def profile_help() -> str:
    schema = PROFILE_SCHEMA
    blocks = [schema["description"]]
    for node in (
        *schema["properties"].values(),
        *schema["$defs"].values(),
    ):
        if "description" in node:
            blocks.append("\n\n".join(describe_schema(node)))
    for example in schema["examples"]:
        blocks.append(
            "```json\n"
            + json.dumps(example, ensure_ascii=False, indent=2)
            + "\n```"
        )
    blocks.append(
        "Profilordner und verfügbare Profile zeigt "
        "`mdman profiles list`. Standardmäßig liegen Benutzerprofile "
        "unter `~/.config/mdman/schemas/`; `XDG_CONFIG_HOME` bestimmt "
        "die Konfigurationsbasis. "
        "`mdman profiles validate` prüft die Profile. "
        "`mdman profiles schema` gibt das vollständige JSON Schema aus."
    )
    return "\n\n".join(blocks)


profiles_app = typer.Typer(
    help="Darstellungsprofile finden, prüfen und ihr Format anzeigen.",
    no_args_is_help=True,
    rich_markup_mode="markdown",
    epilog=profile_help(),
)


@profiles_app.command("list", help="Profilordner und Profile anzeigen.")
def list_profiles() -> None:
    console = Console(highlight=False)
    console.print(Text("Profilverzeichnisse", style="bold"))
    for directory in profile_directories():
        console.print(Text(str(directory)))
    try:
        paths = find_profiles()
    except OSError as error:
        typer.echo(f"mdman: {error}", err=True)
        raise typer.Exit(code=1) from error
    if not paths:
        console.print("Keine Profile gefunden.")
        return
    table = Table("Profil", "Datei", "Status", box=None)
    seen: set[str] = set()
    for path in paths:
        status = "überlagert" if path.stem in seen else "ausgewählt"
        table.add_row(Text(path.stem), Text(str(path)), Text(status))
        seen.add(path.stem)
    console.print(table)


@profiles_app.command(
    "validate",
    help="Ein Profil oder alle gefundenen Profildateien prüfen.",
)
def validate_profiles(
    profile: Annotated[
        str | None,
        typer.Argument(
            help=(
                "Profilname oder JSON-Profilpfad; "
                "ohne Angabe alle Dateien."
            ),
            metavar="PROFIL",
        ),
    ] = None,
) -> None:
    try:
        paths = [profile_path(profile)] if profile else find_profiles()
    except OSError as error:
        typer.echo(f"mdman: {error}", err=True)
        raise typer.Exit(code=1) from error
    if not paths:
        typer.echo("Keine Profile gefunden.")
        return
    console = Console(highlight=False)
    invalid = False
    for path in paths:
        try:
            load_profile(str(path))
        except ProfileError as error:
            console.print(Text(f"✗ {error}", style="red"))
            invalid = True
        else:
            console.print(Text(f"✓ {path}", style="green"))
    if invalid:
        raise typer.Exit(code=1)


@profiles_app.command(
    "schema",
    help="Das verbindliche Profilformat als JSON Schema ausgeben.",
)
def show_profile_schema() -> None:
    typer.echo(json.dumps(PROFILE_SCHEMA, ensure_ascii=False, indent=2))
