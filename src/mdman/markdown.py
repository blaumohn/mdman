from __future__ import annotations

import re
import unicodedata

TOC_START_MARKER = "<!-- mdman:toc:start -->"
TOC_END_MARKER = "<!-- mdman:toc:end -->"

# GitHub entfernt Satzzeichen, behält aber Bindestrich-Minus und
# Unterstrich: "Repository-Aufbau" wird zu "repository-aufbau", nicht
# zu "repositoryaufbau". Beide sind Unicode-Satzzeichen (Pd bzw. Pc)
# und fielen sonst mit weg. Die Ausnahme gilt genau diesen zwei
# ASCII-Zeichen, nicht ihren Kategorien: der Gedankenstrich ist
# ebenfalls Pd und wird weiterhin entfernt.
KEPT_PUNCTUATION = "-_"


def add_toc(source: str, *, add_markers: bool = False) -> str:
    toc_match = find_marked_toc(source)
    heading_source = (
        source if toc_match is None else source[toc_match.end() :]
    )
    headings = _extract_heading_entries(heading_source)
    if not headings:
        if toc_match is not None:
            return replace_marked_toc(source, "", toc_match)
        return source
    first_level = min(level for level, _, _ in headings)
    links = "\n".join(
        f"{'  ' * max(level - first_level, 0)}- [{text}](#{heading_id})"
        for level, text, heading_id in headings
    )
    toc = f"{links}\n\n---"
    if toc_match is not None:
        return replace_marked_toc(source, toc, toc_match)
    if add_markers:
        toc = f"{TOC_START_MARKER}\n{toc}\n{TOC_END_MARKER}"
    return f"{toc}\n\n{source}"


def find_marked_toc(source: str) -> re.Match[str] | None:
    pattern = re.compile(
        rf"^{re.escape(TOC_START_MARKER)}\n.*?"
        rf"^{re.escape(TOC_END_MARKER)}",
        re.MULTILINE | re.DOTALL,
    )
    return pattern.search(source)


def replace_marked_toc(
    source: str, toc: str, toc_match: re.Match[str]
) -> str:
    marked_toc = f"{TOC_START_MARKER}\n{toc}\n{TOC_END_MARKER}"
    return (
        source[: toc_match.start()]
        + marked_toc
        + source[toc_match.end() :]
    )


def extract_headings(source: str) -> list[tuple[str, str]]:
    return [
        (title, heading_id)
        for _, title, heading_id in _extract_heading_entries(source)
    ]


def github_heading_id(title: str) -> str:
    title = title.lower()
    title = "".join(
        character
        for character in title
        if character == " "
        or character in KEPT_PUNCTUATION
        or not (
            character.isspace()
            or unicodedata.category(character).startswith("P")
        )
    )
    return title.strip().replace(" ", "-")


def unique_heading_id(heading_id: str, used_ids: dict[str, int]) -> str:
    occurrence = used_ids.get(heading_id, 0)
    used_ids[heading_id] = occurrence + 1
    return (
        heading_id if occurrence == 0 else f"{heading_id}-{occurrence}"
    )


def _extract_heading_entries(source: str) -> list[tuple[int, str, str]]:
    headings: list[tuple[int, str, str]] = []
    used_ids: dict[str, int] = {}
    fenced = False
    lines = source.splitlines()

    for index, line in enumerate(lines):
        if _is_fence(line):
            fenced = not fenced
            continue
        if fenced or line.startswith(("    ", "\t")):
            continue
        heading = _heading_at(lines, index)
        if heading is None:
            continue
        level, title = heading
        entry = _heading_entry(level, title, used_ids)
        if entry is None:
            continue
        headings.append(entry)
    return headings


def _heading_entry(
    level: int,
    title: str,
    used_ids: dict[str, int],
) -> tuple[int, str, str] | None:
    title = _plain_heading_text(title)
    if not title:
        return None
    heading_id = github_heading_id(title)
    heading_id = unique_heading_id(
        heading_id,
        used_ids,
    )
    return level, title, heading_id


def _heading_at(lines: list[str], index: int) -> tuple[int, str] | None:
    line = lines[index]
    match = re.match(r"^ {0,3}(#{1,6})[ \t]+(.+?)[ \t]*#*[ \t]*$", line)
    if match:
        return len(match.group(1)), match.group(2).strip()
    if index == 0 or not re.match(r"^ {0,3}(=+|-+)[ \t]*$", line):
        return None
    previous = lines[index - 1].strip()
    if not previous or previous.startswith(("#", ">", "-", "*", "+")):
        return None
    level = 1 if line.lstrip().startswith("=") else 2
    return level, previous


def _is_fence(line: str) -> bool:
    return bool(re.match(r"^ {0,3}(```+|~~~+)", line))


def _plain_heading_text(title: str) -> str:
    title = re.sub(r"!\[([^]]*)\]\([^)]*\)", r"\1", title)
    title = re.sub(r"\[([^]]+)\]\([^)]*\)", r"\1", title)
    return re.sub(r"[*_`~]", "", title)
