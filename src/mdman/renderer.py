from __future__ import annotations

import contextlib
import os
import re
import unicodedata
from collections.abc import Iterator
from pathlib import Path

from rich.console import Console
from rich.markdown import Markdown


def render_markdown(
    source: str,
    *,
    width: int = 80,
    pager: bool = False,
    with_toc: bool = False,
) -> None:
    """Render Markdown using Rich's terminal-aware default styles."""
    console = Console(width=width, color_system="auto", highlight=False)
    document = Markdown(markdown_with_toc(source) if with_toc else source, code_theme="ansi_dark")

    if pager:
        with _less_raw_control_codes():
            with console.pager(styles=True, links=False):
                console.print(document)
    else:
        console.print(document)


@contextlib.contextmanager
def _less_raw_control_codes() -> Iterator[None]:
    """Enable ANSI control-code passthrough for the system's less pager."""
    pager = os.environ.get("PAGER", "")
    pager_name = Path(pager.split(maxsplit=1)[0]).name if pager else "less"
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


def markdown_with_toc(source: str) -> str:
    """Prepend a hierarchical Markdown table of contents to a document."""
    headings = _extract_heading_entries(source)
    if not headings:
        return source

    first_level = min(level for level, _, _ in headings)
    links = "\n".join(
        f"{'  ' * max(level - first_level, 0)}- [{text}](#{slug})"
        for level, text, slug in headings
    )
    return f"## Inhaltsverzeichnis\n\n{links}\n\n---\n\n{source}"


def extract_headings(source: str) -> list[tuple[str, str]]:
    """Return ATX and setext headings with unique Markdown anchor slugs."""
    return [(title, slug) for _, title, slug in _extract_heading_entries(source)]


def _extract_heading_entries(source: str) -> list[tuple[int, str, str]]:
    """Return heading levels, titles, and unique Markdown anchor slugs."""
    headings: list[tuple[int, str, str]] = []
    used_slugs: dict[str, int] = {}
    fenced = False
    lines = source.splitlines()

    for index, line in enumerate(lines):
        if _is_fence(line):
            fenced = not fenced
            continue
        if fenced or line.startswith(("    ", "\t")):
            continue

        match = re.match(r"^ {0,3}(#{1,6})[ \t]+(.+?)[ \t]*#*[ \t]*$", line)
        if match:
            level = len(match.group(1))
            title = match.group(2).strip()
        elif index > 0 and re.match(r"^ {0,3}(=+|-+)[ \t]*$", line):
            previous = lines[index - 1].strip()
            if not previous or previous.startswith(("#", ">", "-", "*", "+")):
                continue
            level = 1 if line.lstrip().startswith("=") else 2
            title = previous
        else:
            continue

        plain_title = _plain_heading_text(title)
        if not plain_title:
            continue
        slug = _unique_slug(plain_title, used_slugs)
        headings.append((level, plain_title, slug))

    return headings


def _is_fence(line: str) -> bool:
    return bool(re.match(r"^ {0,3}(```+|~~~+)", line))


def _plain_heading_text(title: str) -> str:
    title = re.sub(r"!\[([^]]*)\]\([^)]*\)", r"\1", title)
    title = re.sub(r"\[([^]]+)\]\([^)]*\)", r"\1", title)
    title = re.sub(r"[*_`~]", "", title)
    return " ".join(title.split())


def _unique_slug(title: str, used_slugs: dict[str, int]) -> str:
    normalized = unicodedata.normalize("NFKD", title)
    ascii_title = normalized.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-zA-Z0-9 -]", "", ascii_title.lower())
    slug = re.sub(r"[ -]+", "-", slug).strip("-") or "heading"
    occurrence = used_slugs.get(slug, 0)
    used_slugs[slug] = occurrence + 1
    return slug if occurrence == 0 else f"{slug}-{occurrence}"
