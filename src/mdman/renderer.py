from __future__ import annotations

import contextlib
import json
import os
import re
from collections.abc import Iterator, Sequence
from pathlib import Path

from rich import box
from rich.console import Console, Group, RenderableType
from rich.markdown import Markdown
from rich.padding import Padding
from rich.panel import Panel
from rich.rule import Rule
from rich.text import Text

from mdman.jsonl import Entry, Field


def render_markdown(
    source: str,
    *,
    width: int = 80,
    pager: bool = False,
) -> None:
    """Render Markdown using Rich's terminal-aware default styles."""
    _print(_markdown(source), width=width, pager=pager)


def render_entries(
    entries: Sequence[Entry],
    *,
    width: int = 80,
    pager: bool = False,
) -> None:
    """Render JSONL entries as headers with embedded Markdown."""
    renderables: list[RenderableType] = []
    for index, entry in enumerate(entries):
        if index:
            renderables.append(Text())
        renderables.extend(_entry_renderables(entry))
    _print(Group(*renderables), width=width, pager=pager)


def _entry_renderables(entry: Entry) -> list[RenderableType]:
    label = "Metadaten" if entry.metadata else f"Zeile {entry.line}"
    return [
        Rule(Text(label), align="left"),
        *_fields_renderables(entry.fields),
    ]


def _fields_renderables(
    fields: Sequence[Field],
) -> list[RenderableType]:
    renderables: list[RenderableType] = []
    for field in fields:
        label = Text(field.name, style="dim")
        if field.kind == "markdown":
            title = (
                Text.assemble(label, " · Markdown")
                if field.name
                else Text("Markdown")
            )
            renderables.append(
                Panel(
                    _markdown(str(field.value)),
                    title=title,
                    title_align="left",
                    box=box.SQUARE,
                )
            )
        elif field.kind in {"object", "list"}:
            if field.name:
                renderables.append(label)
            children = _fields_renderables(field.children)
            if not children:
                children = [
                    Text("{}" if field.kind == "object" else "[]")
                ]
            renderables.append(Padding(Group(*children), (0, 0, 0, 2)))
            renderables.append(Text())
        else:
            value = field.value
            text = (
                value
                if isinstance(value, str)
                else json.dumps(value, ensure_ascii=False)
            )
            if field.name:
                renderables.append(Text.assemble(label, "  ", text))
            else:
                renderables.append(Text.assemble("• ", text))
    return renderables


def _markdown(source: str) -> Markdown:
    return Markdown(source, code_theme="ansi_dark")


def _print(
    renderable: RenderableType, *, width: int, pager: bool
) -> None:
    console = Console(width=width, color_system="auto", highlight=False)
    if pager:
        with (
            _less_raw_control_codes(),
            console.pager(styles=True, links=False),
        ):
            console.print(renderable)
    else:
        console.print(renderable)


@contextlib.contextmanager
def _less_raw_control_codes() -> Iterator[None]:
    pager = os.environ.get("PAGER", "")
    pager_name = (
        Path(pager.split(maxsplit=1)[0]).name if pager else "less"
    )
    if pager_name != "less":
        yield
        return

    previous_less = os.environ.get("LESS")
    less_options = previous_less or ""
    if not re.search(r"(?:^|\s)-[^\s]*[rR]", less_options):
        os.environ["LESS"] = f"{less_options} -R".strip()
    try:
        yield
    finally:
        if previous_less is None:
            os.environ.pop("LESS", None)
        else:
            os.environ["LESS"] = previous_less
