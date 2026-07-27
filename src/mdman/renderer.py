from __future__ import annotations

from rich.console import Console
from rich.markdown import Markdown


def render_markdown(source: str, *, width: int = 80, pager: bool = False) -> None:
    """Render Markdown to stdout without ANSI colour sequences."""
    console = Console(width=width, color_system=None, highlight=False)
    document = Markdown(source, code_theme="ansi_dark")

    if pager:
        with console.pager(styles=False):
            console.print(document)
    else:
        console.print(document)

