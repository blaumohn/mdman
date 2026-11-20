"""Render LaTeX with the bundled parser, Rich, and terminal BiDi."""

from __future__ import annotations

import re
from typing import Any, ClassVar

from markdown_it import MarkdownIt
from markdown_it.rules_block import StateBlock
from markdown_it.rules_core import StateCore
from markdown_it.token import Token
from mdit_py_plugins.dollarmath import dollarmath_plugin
from mdit_py_plugins.texmath import texmath_plugin
from rich import box
from rich.console import Console, ConsoleOptions, RenderResult
from rich.markdown import Markdown, MarkdownElement
from rich.panel import Panel
from rich.text import Text
from unicodeit.data import REPLACEMENTS  # type: ignore[import-untyped]

from mdman._vendor.pylatexenc import latex2text, latexwalker, macrospec
from mdman._vendor.pylatexenc.latexnodes import (
    ParsingStateDeltaLeaveMathMode,
)
from mdman.bidi import BidiConsole, has_rtl


def _literal_text(node: Any, l2tobj: Any) -> Any:
    # Preserve literal text and its explicit spaces, including Hebrew
    # prefixes directly attached to a math variable: \text{ב-}C.
    in_math = l2tobj.state.in_math_mode
    with l2tobj.push_state(in_math_mode=False):
        text = l2tobj.node_arg_to_text(node, 0)
    return (
        l2tobj.make_math_piece(text=text, cls="ord")
        if in_math
        else text
    )


def _delimiter_text(node: Any, l2tobj: Any) -> Any:
    text = l2tobj.node_arg_to_text(node, 0)
    if text == ".":
        return ""
    edge = "open" if node.macroname == "left" else "close"
    return l2tobj.make_math_piece(text=text, cls=edge)


def _boxed_text(node: Any, l2tobj: Any) -> str:
    return f"⟦{l2tobj.node_arg_to_text(node, 0)}⟧"


def _minipage_text(node: Any, l2tobj: Any) -> Any:
    # The size and alignment arguments are consumed by the parser. The
    # terminal lays out the body as prose with its own inline formulas.
    in_math = l2tobj.state.in_math_mode
    with l2tobj.push_state(in_math_mode=False):
        text = l2tobj.nodelist_to_text(node.nodelist).strip()
    return (
        l2tobj.make_math_piece(text=text, cls="ord")
        if in_math
        else text
    )


_PARSE_CONTEXT = latexwalker.get_default_latex_context_db()
_PARSE_CONTEXT.add_context_category(
    "mdman",
    macros=[
        macrospec.MacroSpec(name, "{")
        for name in ("boxed", "left", "right")
    ],
    environments=[
        macrospec.EnvironmentSpec(
            "minipage",
            "[[[{",
            body_parsing_state_delta=ParsingStateDeltaLeaveMathMode(),
        )
    ],
    prepend=True,
)
_TEXT_CONTEXT = latex2text.get_default_latex_context_db()
_TEXT_CONTEXT.add_context_category(
    "mdman",
    macros=[
        latex2text.MacroTextSpec("boxed", simplify_repl=_boxed_text),
        latex2text.MacroTextSpec("centering", discard=True),
        latex2text.MacroTextSpec("par", simplify_repl="\n\n"),
        latex2text.MacroTextSpec("text", simplify_repl=_literal_text),
        latex2text.MacroTextSpec("left", simplify_repl=_delimiter_text),
        latex2text.MacroTextSpec(
            "right", simplify_repl=_delimiter_text
        ),
    ],
    environments=[
        latex2text.EnvironmentTextSpec("minipage", _minipage_text)
    ],
    prepend=True,
)


# Match whole command names so a known prefix in an unknown command
# (e.g. \iffunknown) does not get replaced.
_SYMBOLS = {
    name[1:]: symbol
    for name, symbol in REPLACEMENTS
    if name.startswith("\\")
    and name[1:].isascii()
    and name[1:].isalpha()
}


class _LatexText(latex2text.LatexNodes2Text):
    def macro_node_to_text(self, node: Any) -> Any:
        # The library normally drops unknown commands. Keep the whole
        # formula as source instead, so no mathematical meaning is lost.
        if node.macroname in {"input", "include"}:
            raise ValueError("Unsupported macro")
        if self.latex_context.get_macro_spec(node.macroname) is None:
            if node.macroname in _SYMBOLS:
                return _SYMBOLS[node.macroname]
            raise ValueError("Unsupported macro")
        return super().macro_node_to_text(node)

    def environment_node_to_text(self, node: Any) -> Any:
        if (
            self.latex_context.get_environment_spec(
                node.environmentname
            )
            is None
        ):
            raise ValueError("Unsupported environment")
        return super().environment_node_to_text(node)


def _formula(source: str) -> tuple[str, bool] | None:
    try:
        nodes, _, _ = latexwalker.LatexWalker(
            r"\(" + source + r"\)",
            latex_context=_PARSE_CONTEXT,
            tolerant_parsing=False,
        ).get_latex_nodes()
        math = nodes[0]
        content = [
            node
            for node in math.nodelist
            if not (
                node.isNodeType(latexwalker.LatexCharsNode)
                and not node.chars.strip()
            )
        ]
        framed = (
            len(content) == 1
            and content[0].isNodeType(latexwalker.LatexMacroNode)
            and content[0].macroname == "boxed"
        )
        if framed:
            argument = content[0].nodeargd.argnlist[0]
            math.nodelist = (
                argument.nodelist
                if argument.isNodeType(latexwalker.LatexGroupNode)
                else [argument]
            )
        converter = _LatexText(
            latex_context=_TEXT_CONTEXT,
            math_fontstyle=None,
            text_fontstyle=None,
        )
        return converter.nodelist_to_text(nodes).strip(), framed
    except (
        ValueError,
        RecursionError,
        latexwalker.LatexWalkerParseError,
    ):
        return None


_BRACKET_OR_ESCAPE = re.compile(r"\\(?:[\\%\[\]])|%.*")


def _nested_bracket_block(
    state: StateBlock, start: int, end: int, silent: bool
) -> bool:
    begin = state.bMarks[start] + state.tShift[start]
    if state.is_code_block(start) or not state.src.startswith(
        r"\[", begin
    ):
        return False

    # texmath ends at the first \]. Intercept balanced nested blocks
    # so display math inside a minipage stays with the surrounding box.
    depth = 1
    nested = False
    body = []
    for line in range(start, end):
        if (
            not state.isEmpty(line)
            and state.sCount[line] < state.blkIndent
        ):
            break
        first = begin + 2 if line == start else state.bMarks[line]
        source = state.src[first : state.eMarks[line]]
        for match in _BRACKET_OR_ESCAPE.finditer(source):
            delimiter = match[0]
            if delimiter == r"\[":
                depth += 1
                nested = True
            if delimiter != r"\]":
                continue
            depth -= 1
            if depth:
                continue
            if not nested or source[match.end() :].strip():
                return False
            if not silent:
                body.append(source[: match.start()])
                token = state.push("math_block", "math", 0)
                token.content = "\n".join(body)
                token.markup = r"\["
                token.map = [start, line + 1]
            state.line = line + 1
            return True
        body.append(source)
    return False


def _boxed_paragraphs(state: StateCore) -> None:
    # Compatibility with the plain [ \boxed{...} ] spelling.
    tokens = state.tokens
    for index in range(len(tokens) - 2):
        opening, inline, closing = tokens[index : index + 3]
        if (
            opening.type == "paragraph_open"
            and inline.type == "inline"
            and closing.type == "paragraph_close"
        ):
            source = inline.content.strip()
            if (
                source.startswith("[")
                and source.endswith("]")
                and source[1:-1].strip().startswith(r"\boxed")
            ):
                opening.type = "math_block"
                opening.nesting = 0
                opening.markup = "["
                opening.content = source[1:-1]
                inline.type = closing.type = "mdman_math_skip"
    state.tokens = [
        token for token in tokens if token.type != "mdman_math_skip"
    ]


def _convert_tokens(tokens: list[Token]) -> None:
    for token in tokens:
        if token.children:
            _convert_tokens(token.children)
        if token.type not in {"math_inline", "math_block"}:
            continue
        converted = _formula(token.content)
        if converted is None:
            left = token.markup
            right = {r"\[": r"\]", r"\(": r"\)", "[": "]"}.get(
                left, left
            )
            converted = (f"{left}{token.content}{right}", False)
        text, framed = converted
        if token.type == "math_inline":
            token.type = "text"
            token.content = f"⟦{text}⟧" if framed else text
        else:
            token.type = "mdman_math"
            token.content = text
            token.meta["framed"] = framed


def _render_math(state: StateCore) -> None:
    _convert_tokens(state.tokens)


class _MathElement(MarkdownElement):
    text: str
    framed: bool

    @classmethod
    def create(cls, _markdown: Markdown, token: Token) -> _MathElement:
        element = cls()
        element.text = token.content
        element.framed = token.meta["framed"]
        return element

    def __rich_console__(
        self, console: Console, options: ConsoleOptions
    ) -> RenderResult:
        text = Text(self.text)
        if self.framed:
            # Match the existing RTL Markdown field frames: vertical
            # edges can be moved into the text by terminal BiDi engines.
            frame = (
                box.HORIZONTALS
                if isinstance(console, BidiConsole)
                and has_rtl(self.text)
                else box.SQUARE
            )
            yield Panel(text, box=frame, expand=False)
        else:
            yield text


class MathMarkdown(Markdown):
    elements: ClassVar[dict[str, type[MarkdownElement]]] = {
        **Markdown.elements,
        "mdman_math": _MathElement,
    }

    def __init__(self, source: str) -> None:
        super().__init__(source, code_theme="ansi_dark")
        parser = MarkdownIt().enable("strikethrough").enable("table")
        parser.use(texmath_plugin, delimiters="brackets")
        parser.block.ruler.before(
            "math_block_eqno",
            "mdman_nested_math",
            _nested_bracket_block,
        )
        parser.use(
            dollarmath_plugin,
            allow_space=False,
            allow_digits=False,
            allow_labels=False,
        )
        parser.core.ruler.before(
            "inline", "mdman_box", _boxed_paragraphs
        )
        parser.core.ruler.after("inline", "mdman_math", _render_math)
        self.parsed = parser.parse(source)
