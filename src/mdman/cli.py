from __future__ import annotations

import contextlib
import os
import stat
import sys
import tempfile
from enum import Enum
from pathlib import Path
from typing import Annotated, Any

import typer
from typer.core import TyperGroup

from mdman import __version__
from mdman.jsonl import JsonlError, read_entries
from mdman.markdown import add_toc
from mdman.profile_commands import profile_help, profiles_app
from mdman.profiles import ProfileError, load_profile
from mdman.renderer import render_entries, render_markdown


class OutputFormat(str, Enum):
    TERMINAL = "terminal"
    MARKDOWN = "markdown"


RENDER_COMMAND = "render"


class DefaultRenderGroup(TyperGroup):
    """`mdman DATEI` bleibt Kurzform für `mdman render DATEI`."""

    def parse_args(self, ctx: Any, args: list[str]) -> list[str]:
        first = args[0] if args else None
        if first not in {*self.commands, "--help"}:
            args = [RENDER_COMMAND, *args]
        return super().parse_args(ctx, args)

    def format_help(self, ctx: Any, formatter: Any) -> None:
        super().format_help(ctx, formatter)
        render = self.commands[RENDER_COMMAND]
        with typer.Context(
            render, parent=ctx, info_name=RENDER_COMMAND
        ) as render_ctx:
            render.format_help(render_ctx, formatter)


app = typer.Typer(
    cls=DefaultRenderGroup,
    add_completion=False,
    rich_markup_mode="markdown",
    help="Markdown lesbar und monochrom im Terminal anzeigen.",
    epilog="Kurzform: mdman DATEI entspricht mdman render DATEI.",
)
app.add_typer(profiles_app, name="profiles")


def main() -> None:
    app(prog_name="mdman")


@app.command(
    RENDER_COMMAND, help="Markdown im Terminal anzeigen (Standard)."
)
def render_command(
    filename: Annotated[
        str | None,
        typer.Argument(
            help="Markdown-Datei; '-' liest von stdin.",
            metavar="DATEI",
        ),
    ] = None,
    width: Annotated[
        int,
        typer.Option(
            "-w",
            "--width",
            min=20,
            help="Ausgabebreite in Zeichen.",
        ),
    ] = 80,
    pager: Annotated[
        bool,
        typer.Option(
            "-p",
            "--pager",
            help="Ausgabe über den konfigurierten Pager anzeigen.",
        ),
    ] = False,
    toc: Annotated[
        bool,
        typer.Option(
            "--toc",
            help="Inhaltsverzeichnis in das Dokument einfügen.",
        ),
    ] = False,
    output_format: Annotated[
        OutputFormat | None,
        typer.Option("--format", help="Ausgabeformat."),
    ] = None,
    in_place: Annotated[
        bool,
        typer.Option(
            "-i",
            "--in-place",
            help="Markdown mit TOC in dieselbe Datei zurückschreiben.",
        ),
    ] = False,
    _version: Annotated[
        bool,
        typer.Option(
            "--version",
            callback=print_version,
            is_eager=True,
            help="Version ausgeben.",
        ),
    ] = False,
) -> None:
    try:
        if in_place and (filename is None or filename == "-"):
            raise typer.BadParameter(
                "benötigt eine Markdown-Datei, nicht stdin",
                param_hint="-i",
            )
        if in_place and not toc:
            raise typer.BadParameter(
                "ist nur zusammen mit --toc sinnvoll",
                param_hint="-i",
            )
        if in_place and output_format is OutputFormat.TERMINAL:
            raise typer.BadParameter(
                "ist mit --format terminal nicht kombinierbar",
                param_hint="--format",
            )
        if in_place and pager:
            raise typer.BadParameter(
                "ist mit --pager nicht kombinierbar",
                param_hint="--pager",
            )
        source = read_source(filename)
        effective_format = (
            OutputFormat.MARKDOWN if in_place else output_format
        )
        if effective_format is OutputFormat.MARKDOWN and pager:
            raise typer.BadParameter(
                "ist mit --format markdown nicht kombinierbar",
                param_hint="--pager",
            )
        if toc:
            source = add_toc(source, markers=in_place)
        if in_place:
            assert filename is not None and filename != "-"
            write_source_in_place(filename, source)
        elif effective_format is OutputFormat.MARKDOWN:
            typer.echo(source, nl=False)
        else:
            render_markdown(source, width=width, pager=pager)
    except (OSError, UnicodeError) as error:
        typer.echo(f"mdman: {error}", err=True)
        raise typer.Exit(code=1) from error


@app.command(
    "jsonl",
    help="JSONL mit einem Darstellungsprofil anzeigen.",
    epilog=profile_help(),
)
def jsonl_command(
    profile: Annotated[
        str,
        typer.Argument(
            help="Profilname oder JSON-Profilpfad.", metavar="PROFIL"
        ),
    ],
    filename: Annotated[
        str | None,
        typer.Argument(
            help="JSONL-Datei; '-' oder keine Datei liest stdin.",
            metavar="DATEI",
        ),
    ] = None,
    width: Annotated[
        int,
        typer.Option(
            "-w", "--width", min=20, help="Ausgabebreite in Zeichen."
        ),
    ] = 80,
    pager: Annotated[
        bool,
        typer.Option(
            "-p", "--pager", help="Ausgabe über den Pager anzeigen."
        ),
    ] = False,
) -> None:
    try:
        selected_profile = load_profile(profile)
        entries = read_entries(
            read_source(filename), profile=selected_profile
        )
        render_entries(entries, width=width, pager=pager)
    except (OSError, UnicodeError, JsonlError, ProfileError) as error:
        typer.echo(f"mdman: {error}", err=True)
        raise typer.Exit(code=1) from error


def print_version(value: bool) -> bool:
    if value:
        typer.echo(f"mdman {__version__}")
        raise typer.Exit()
    return value


def read_source(filename: str | None) -> str:
    if filename is None or filename == "-":
        return sys.stdin.read()
    return Path(filename).read_text(encoding="utf-8")


def write_source_in_place(filename: str, source: str) -> None:
    path = Path(filename)
    if not path.is_file():
        raise OSError(f"keine reguläre Datei: {path}")
    mode = stat.S_IMODE(path.stat().st_mode)
    temporary_name: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as temporary:
            temporary_name = temporary.name
            temporary.write(source)
            temporary.flush()
            os.fsync(temporary.fileno())
        os.chmod(temporary_name, mode)
        os.replace(temporary_name, path)
        temporary_name = None
    finally:
        if temporary_name is not None:
            with contextlib.suppress(FileNotFoundError):
                os.unlink(temporary_name)
