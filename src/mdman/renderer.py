from __future__ import annotations

import contextlib
import json
import os
import re
import shlex
import subprocess
from collections.abc import Iterator, Sequence
from pathlib import Path

from markdown_it.token import Token
from rich import box
from rich.console import Console, Group, RenderableType
from rich.markdown import Markdown
from rich.padding import Padding
from rich.pager import Pager, SystemPager
from rich.panel import Panel
from rich.rule import Rule
from rich.text import Text

from mdman.bidi import BidiConsole, has_rtl
from mdman.jsonl import Entry, Field
from mdman.math import MathMarkdown

_CITATION_MARKER = re.compile(
    r"(?:\ue200|<U\+E200>)cite"
    r"(?:\s*(?:\ue202|<U\+E202>)\s*turn[0-9]+[a-z]+[0-9]+)+"
    r"\s*(?:\ue201|<U\+E201>)"
    r"|[\ue200-\ue202]|<U\+E20[0-2]>",
    re.IGNORECASE,
)


def render_markdown(
    source: str,
    *,
    width: int = 80,
    pager: bool = False,
) -> None:
    """Render Markdown using Rich's terminal-aware default styles."""
    console = _console(width, pager)
    _print(_markdown(source), console=console, pager=pager)


def render_entries(
    entries: Sequence[Entry],
    *,
    width: int = 80,
    pager: bool = False,
) -> None:
    """Render JSONL entries as headers with embedded Markdown."""
    console = _console(width, pager)
    bidi_layout = isinstance(console, BidiConsole)
    renderables: list[RenderableType] = []
    for index, entry in enumerate(entries):
        if index:
            renderables.append(Text())
        renderables.extend(_entry_renderables(entry, bidi_layout))
    _print(Group(*renderables), console=console, pager=pager)


def _entry_renderables(
    entry: Entry, bidi_layout: bool
) -> list[RenderableType]:
    label = "Metadaten" if entry.metadata else f"Zeile {entry.line}"
    return [
        Rule(Text(label), align="left"),
        *_fields_renderables(entry.fields, bidi_layout),
    ]


def _fields_renderables(
    fields: Sequence[Field],
    bidi_layout: bool,
) -> list[RenderableType]:
    renderables: list[RenderableType] = []
    for field in fields:
        label = Text(field.name, style="dim")
        value = field.value
        if isinstance(value, str) and field.kind == "string":
            value = _CITATION_MARKER.sub("", value)
        if field.kind == "markdown":
            source = str(value)
            title = (
                Text.assemble(label, " · Markdown")
                if field.name
                else Text("Markdown")
            )
            frame = (
                box.HORIZONTALS
                if bidi_layout
                and (has_rtl(source) or has_rtl(field.name))
                else box.SQUARE
            )
            renderables.append(
                Panel(
                    _markdown(source),
                    title=title,
                    title_align="left",
                    box=frame,
                )
            )
        elif field.kind in {"object", "list"}:
            if field.name:
                renderables.append(label)
            children = _fields_renderables(field.children, bidi_layout)
            if not children:
                children = [
                    Text("{}" if field.kind == "object" else "[]")
                ]
            renderables.append(Padding(Group(*children), (0, 0, 0, 2)))
            renderables.append(Text())
        else:
            text = (
                value
                if isinstance(value, str)
                else json.dumps(value, ensure_ascii=False)
            )
            if (
                bidi_layout
                and field.name
                and (has_rtl(text) or has_rtl(field.name))
            ):
                renderables.extend(
                    (label, Padding.indent(Text(text), 2))
                )
            elif field.name:
                renderables.append(Text.assemble(label, "  ", text))
            else:
                renderables.append(Text.assemble("• ", text))
    return renderables


def _markdown(source: str) -> Markdown:
    markdown = MathMarkdown(source)
    _hide_citation_markers(markdown.parsed)
    return markdown


def _hide_citation_markers(tokens: list[Token]) -> None:
    for token in tokens:
        if token.type in {"text", "mdman_math"}:
            token.content = _CITATION_MARKER.sub("", token.content)
        if token.children:
            _hide_citation_markers(token.children)


def _console(width: int, pager: bool) -> Console:
    console = Console(highlight=False)
    terminal = console.is_terminal
    if terminal:
        width = min(width, console.width)
    if terminal or pager:
        bidi_console = BidiConsole(width=width, highlight=False)
        bidi_console.embed_rtl = terminal and (
            not pager or _less_passes_direction_marks()
        )
        return bidi_console
    console.width = width
    return console


def _print(
    renderable: RenderableType, *, console: Console, pager: bool
) -> None:
    if pager:
        with console.pager(
            pager=_TerminalPager(), styles=True, links=False
        ):
            console.print(renderable)
    else:
        console.print(renderable)


class _TerminalPager(Pager):
    def show(self, content: str) -> None:
        with _less_raw_control_codes(repaint=has_rtl(content)):
            SystemPager().show(content)


@contextlib.contextmanager
def _less_raw_control_codes(*, repaint: bool = False) -> Iterator[None]:
    if not _less_command():
        yield
        return

    previous_less = os.environ.get("LESS")
    less_options = previous_less or ""
    if not re.search(r"(?:^|\s)-[^\s]*[rR]", less_options):
        less_options = f"{less_options} -R".strip()
    if repaint:
        # Partial scrolling can leave stale BiDi rows when changing
        # direction (Ctrl-D, then Ctrl-U). Repaint from the top instead.
        less_options = f"{less_options} -c -h0 -y0".strip()
    os.environ["LESS"] = less_options
    try:
        yield
    finally:
        if previous_less is None:
            os.environ.pop("LESS", None)
        else:
            os.environ["LESS"] = previous_less


def _less_command() -> list[str]:
    pager = (
        os.environ.get("MANPAGER") or os.environ.get("PAGER") or "less"
    )
    try:
        command = shlex.split(pager)
    except ValueError:
        return []
    return (
        command if command and Path(command[0]).name == "less" else []
    )


def _less_passes_direction_marks() -> bool:
    command = _less_command()
    if not command:
        return False
    options = " ".join((*command[1:], os.environ.get("LESS", "")))
    if re.search(r"(?:^|\s)-(?:[^\s-]*U|\-UNDERLINE-SPECIAL)", options):
        return False
    try:
        result = subprocess.run(
            [command[0], "--version"],
            capture_output=True,
            check=True,
            timeout=1,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    version = re.match(rb"less (\d+)\b", result.stdout)
    # Older less versions print Unicode format characters in hex.
    return version is not None and int(version[1]) >= 529
