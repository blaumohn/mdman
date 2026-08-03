from __future__ import annotations

import contextlib
import os
import re
from collections.abc import Iterator
from pathlib import Path

from rich.console import Console
from rich.markdown import Markdown


def render_markdown(
    source: str,
    *,
    width: int = 80,
    pager: bool = False,
) -> None:
    """Render Markdown using Rich's terminal-aware default styles."""
    console = Console(width=width, color_system="auto", highlight=False)
    document = Markdown(source, code_theme="ansi_dark")

    if pager:
        with _less_raw_control_codes():
            with console.pager(styles=True, links=False):
                console.print(document)
    else:
        console.print(document)


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
