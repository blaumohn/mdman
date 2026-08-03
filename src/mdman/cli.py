from __future__ import annotations

import sys
from enum import Enum
from pathlib import Path
from typing import Annotated

import typer

from mdman import __version__
from mdman.markdown import add_toc
from mdman.renderer import render_markdown


class OutputFormat(str, Enum):
    TERMINAL = "terminal"
    MARKDOWN = "markdown"


app = typer.Typer(
    no_args_is_help=False,
    add_completion=False,
    help="Markdown lesbar und monochrom im Terminal anzeigen.",
)


def main() -> None:
    app(prog_name="mdman")


@app.command()
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
        OutputFormat,
        typer.Option("--format", help="Ausgabeformat."),
    ] = OutputFormat.TERMINAL,
    version: Annotated[
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
        source = read_source(filename)
        if output_format is OutputFormat.MARKDOWN and pager:
            raise typer.BadParameter(
                "ist mit --format markdown nicht kombinierbar",
                param_hint="--pager",
            )
        if toc:
            source = add_toc(source)
        if output_format is OutputFormat.MARKDOWN:
            typer.echo(source, nl=False)
        else:
            render_markdown(source, width=width, pager=pager)
    except (OSError, UnicodeError) as error:
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
