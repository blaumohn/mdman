from __future__ import annotations

import re
from collections.abc import Iterable
from unicodedata import bidirectional

from rich._wrap import divide_line
from rich.cells import cell_len
from rich.console import Console, ConsoleOptions, RenderableType
from rich.containers import Lines
from rich.segment import Segment
from rich.text import Text

_RTL_TYPES = {"R", "AL"}
_STRONG_TYPES = _RTL_TYPES | {"L"}


def has_rtl(text: str) -> bool:
    return not text.isascii() and any(
        bidirectional(character) in _RTL_TYPES for character in text
    )


def _direction(text: str) -> str | None:
    for character in text:
        direction = bidirectional(character)
        if direction in _STRONG_TYPES:
            return direction
    return None


def _wrap_offsets(text: str, width: int, *, fold: bool) -> list[int]:
    if _direction(text) not in _RTL_TYPES:
        return divide_line(text, width, fold=fold)

    # Keep short Latin runs and numbers with their preceding RTL word
    # so the next line starts in RTL. The replacement is only for Rich's
    # word-boundary calculation. The original Text supplies the output.
    wrap_text = list(text)
    rtl_start: int | None = None
    group_width = 0
    previous_end = 0
    for word in re.finditer(r"\S+", text):
        if _direction(word[0]) in _RTL_TYPES:
            rtl_start = word.start()
            group_width = cell_len(word[0])
        elif rtl_start is not None:
            group_width += cell_len(text[previous_end : word.end()])
            if group_width <= width:
                group = text[rtl_start : word.end()]
                wrap_text[rtl_start : word.end()] = group.replace(
                    " ", "_"
                )
        previous_end = word.end()
    return divide_line("".join(wrap_text), width, fold=fold)


class BidiConsole(Console):
    """Wrap mixed-direction text for the terminal's BiDi renderer."""

    embed_rtl = False

    def render(
        self,
        renderable: RenderableType,
        options: ConsoleOptions | None = None,
    ) -> Iterable[Segment]:
        options = options or self.options
        if (
            isinstance(renderable, Text)
            and options.max_width > 0
            and has_rtl(renderable.plain)
        ):
            yield from self._render_bidi(renderable, options)
        else:
            yield from super().render(renderable, options)

    def _render_bidi(
        self, text: Text, options: ConsoleOptions
    ) -> Iterable[Segment]:
        justify = text.justify or options.justify or "default"
        overflow = text.overflow or options.overflow or "fold"
        no_wrap = (
            options.no_wrap if text.no_wrap is None else text.no_wrap
        )
        if no_wrap or overflow == "ignore":
            yield from super().render(text, options)
            return

        width = options.max_width
        tab_size = text.tab_size or self.tab_size or 8
        result = Lines()
        for paragraph in text.split(allow_blank=True):
            paragraph.expand_tabs(tab_size)
            lines = paragraph.divide(
                _wrap_offsets(
                    paragraph.plain, width, fold=overflow == "fold"
                )
            )
            for line in lines:
                line.rstrip_end(width)
            lines.justify(self, width, justify, overflow)
            for line in lines:
                line.truncate(width, overflow=overflow)
            if (
                self.embed_rtl
                and _direction(paragraph.plain) in _RTL_TYPES
            ):
                lines = Lines(_rtl_embedding(line) for line in lines)
            result.extend(lines)
        yield from Text("\n").join(result).render(self, end=text.end)


def _rtl_embedding(line: Text) -> Text:
    plain = line.plain
    start = len(plain) - len(plain.lstrip())
    end = len(plain.rstrip())
    if start >= end:
        return line
    # Keep padding and frame characters outside the directional range.
    return Text.assemble(
        line[:start], "\u202b", line[start:end], "\u202c", line[end:]
    )
