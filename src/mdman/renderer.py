from __future__ import annotations

import re
import unicodedata

from rich.console import Console
from rich.markdown import Markdown


def render_markdown(
    source: str,
    *,
    width: int = 80,
    pager: bool = False,
    with_toc: bool = False,
) -> None:
    """Render Markdown to stdout without ANSI colour sequences."""
    console = Console(width=width, color_system=None, highlight=False)
    document = Markdown(markdown_with_toc(source) if with_toc else source, code_theme="ansi_dark")

    if pager:
        with console.pager(styles=False):
            console.print(document)
    else:
        console.print(document)


def markdown_with_toc(source: str) -> str:
    """Prepend a Markdown table of contents to a document."""
    headings = extract_headings(source)
    if not headings:
        return source

    links = "\n".join(f"- [{text}](#{slug})" for text, slug in headings)
    return f"## Inhaltsverzeichnis\n\n{links}\n\n---\n\n{source}"


def extract_headings(source: str) -> list[tuple[str, str]]:
    """Return ATX and setext headings with unique Markdown anchor slugs."""
    headings: list[tuple[str, str]] = []
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
            title = match.group(2).strip()
        elif index > 0 and re.match(r"^ {0,3}(=+|-+)[ \t]*$", line):
            previous = lines[index - 1].strip()
            if not previous or previous.startswith(("#", ">", "-", "*", "+")):
                continue
            title = previous
        else:
            continue

        plain_title = _plain_heading_text(title)
        if not plain_title:
            continue
        slug = _unique_slug(plain_title, used_slugs)
        headings.append((plain_title, slug))

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
