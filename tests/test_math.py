import json
import re
from pathlib import Path
from unittest.mock import PropertyMock, patch

import pytest
from typer.testing import CliRunner

from mdman.cli import app

FORMULA = (
    r"\boxed{ \text{מבנה סמנטי ב-}C \leftrightarrow "
    r"\text{חוויה/רעיון} \leftrightarrow "
    r"\text{המשך הדינמיקה של }C. }"
)
VISIBLE = "מבנה סמנטי ב-C ↔ חוויה/רעיון ↔ המשך הדינמיקה של C."
runner = CliRunner()


@pytest.mark.parametrize(
    "delimiters", [(r"\[", r"\]"), ("$$", "$$"), ("[", "]")]
)
def test_hebrew_formula(delimiters: tuple[str, str]) -> None:
    left, right = delimiters
    result = runner.invoke(
        app, ["-"], input=f"{left}\n{FORMULA}\n{right}"
    )
    assert result.exit_code == 0, result.output
    assert VISIBLE in result.output
    assert "┌" in result.output
    assert "\\text" not in result.output
    assert "\\boxed" not in result.output
    assert result.output.count("↔") == 2


def test_terminal_formula_keeps_existing_rtl_layout() -> None:
    with patch(
        "mdman.renderer.Console.is_terminal",
        new_callable=PropertyMock,
        return_value=True,
    ):
        result = runner.invoke(
            app,
            ["-"],
            input=f"[ {FORMULA} ]",
            env={"COLUMNS": "80", "TERM": "xterm-256color"},
        )
    assert result.exit_code == 0, result.output
    assert f"\u202b{VISIBLE}\u202c" in result.output
    assert "─" in result.output
    assert "│" not in result.output


def test_formula_wraps_at_terminal_width() -> None:
    result = runner.invoke(
        app, ["-w", "25", "-"], input=f"[ {FORMULA} ]"
    )
    assert result.exit_code == 0, result.output
    assert all(len(line) <= 25 for line in result.output.splitlines())
    assert "חוויה/רעיון" in result.output
    assert result.output.count("↔") == 2


@pytest.mark.parametrize("options", ["", "[t][2em][c]"])
def test_boxed_minipage_renders_hebrew_and_math(options: str) -> None:
    source = "\n".join(
        f"  {line:<76}"
        for line in (
            r"\[",
            r"\boxed{",
            rf"\begin{{minipage}}{options}{{0.8\linewidth}}",
            r"שלום עולם: \(x^2\)\\",
            r"המשך ב-C.",
            r"\end{minipage}",
            "}",
            r"\]",
        )
    )
    result = runner.invoke(app, ["-"], input=source)
    assert result.exit_code == 0, result.output
    assert "┌" in result.output
    assert "שלום עולם: x²" in result.output
    assert "המשך ב-C." in result.output
    assert r"\begin" not in result.output
    assert "0.8" not in result.output


def test_boxed_minipage_keeps_nested_display_math() -> None:
    source = r"""
\[
\boxed{\begin{minipage}{0.8\linewidth}
\centering שלום\par
\[x^2 + \alpha\]
המשך.
\end{minipage}}
\]

Outside the box.
"""
    result = runner.invoke(app, ["-"], input=source)
    assert result.exit_code == 0, result.output
    body = [
        line.strip("│ ")
        for line in result.output.splitlines()
        if line.startswith("│")
    ]
    assert [line for line in body if line] == [
        "שלום",
        "x² + α",
        "המשך.",
    ]
    assert "Outside the box." in result.output


def test_inline_formula_and_regular_markdown() -> None:
    result = runner.invoke(
        app,
        ["-"],
        input=r"**Text**: \(A \leftrightarrow B\). [Link](https://example.org)",
    )
    assert result.exit_code == 0, result.output
    assert re.search(r"Text: A\s+↔\s+B\. Link", result.output)


@pytest.mark.parametrize(
    "formula",
    [
        r"\unknown{x}",
        r"\begin{unknown}x\end{unknown}",
        r"\boxed{a",
        r"\boxed{\begin{minipage}{0.8\linewidth}",
    ],
)
def test_unsupported_math_stays_visible(formula: str) -> None:
    source = rf"\[ {formula} \]"
    result = runner.invoke(app, ["-"], input=source)
    assert result.exit_code == 0, result.output
    assert source in result.output


def test_code_and_markdown_export_keep_source() -> None:
    source = f"[ {FORMULA} ]"
    for arguments, content in (
        (["-"], f"```latex\n{source}\n```"),
        (["-"], f"`{source}`"),
        (["--format", "markdown", "-"], source),
    ):
        result = runner.invoke(app, arguments, input=content)
        assert result.exit_code == 0, result.output
        assert r"\boxed" in result.output
        assert r"\leftrightarrow" in result.output
        assert "↔" not in result.output


def test_jsonl_markdown_uses_math_renderer(tmp_path: Path) -> None:
    profile = tmp_path / "profile.json"
    profile.write_text(
        '{"schema":{"body":"markdown"}}', encoding="utf-8"
    )
    source = json.dumps({"body": f"[ {FORMULA} ]"}, ensure_ascii=False)
    result = runner.invoke(app, ["jsonl", str(profile)], input=source)
    assert result.exit_code == 0, result.output
    assert VISIBLE in result.output
    assert result.output.count("↔") == 2


@pytest.mark.parametrize(
    ("formula", "expected"),
    [
        (
            r"P(H\mid D) \propto P(D\mid H)\cdot P(H)",
            "P(H|D) ∝ P(D|H) · P(H)",
        ),
        (r"\frac{a+b}{c}", "(a + b)/c"),
        (r"x^2+a_{ij}", "x² + aᵢⱼ"),
        (r"\sqrt{x}+\sum_{i=1}^n \alpha_i", "√x + ∑ᵢ₌₁ⁿ αᵢ"),
        (r"\left(\frac{a}{b}\right)", "( a/b )"),
        (r"\left. x\right|_0^1", "x|₀¹"),
        (r"\mathbb{R}\subseteq\mathbb{C}", "ℝ ⊆ ℂ"),
        (r"\begin{pmatrix}a&b\\c&d\end{pmatrix}", "[ a b; c d ]"),
        (r"a+\boxed{b}", "a + ⟦b⟧"),
        (r"\boxed a", "│ a │"),
    ],
)
def test_general_latex(formula: str, expected: str) -> None:
    result = runner.invoke(app, ["-"], input=rf"\[ {formula} \]")
    assert result.exit_code == 0, result.output
    assert expected in result.output


def test_adjacent_display_blocks() -> None:
    source = "Before\n\n\\[x^2\\]\n\\[\\alpha\\]\n\nAfter"
    result = runner.invoke(app, ["-"], input=source)
    assert result.exit_code == 0, result.output
    assert re.search(r"Before\s+x²\s+α\s+After", result.output)


def test_dollar_math_keeps_code_and_prices() -> None:
    source = r"Value $x^2$, code `$x^2$`, prices $5 and $10."
    result = runner.invoke(app, ["-"], input=source)
    assert result.exit_code == 0, result.output
    assert "Value x², code $x^2$, prices $5 and $10." in result.output


def test_unknown_inline_math_keeps_source() -> None:
    source = r"Text $\unknown{x}$ and \(\unknown{y}\)."
    result = runner.invoke(app, ["-"], input=source)
    assert result.exit_code == 0, result.output
    assert source in result.output


def test_multiline_equivalence_with_padding() -> None:
    source = "\n".join(
        f"  {line:<76}"
        for line in (
            r"\[",
            r"h\sim h'",
            r"\iff",
            r"P(F\mid h)=P(F\mid h').",
            r"\]",
        )
    )
    result = runner.invoke(app, ["-"], input=source)
    assert result.exit_code == 0, result.output
    assert "h ∼ h' ⇔ P(F|h) = P(F|h')." in result.output
    assert "\\" not in result.output


@pytest.mark.parametrize(
    ("command", "symbol"),
    [(r"\iff", "⇔"), (r"\implies", "⟹"), (r"\impliedby", "⟸")],
)
def test_symbol_aliases_from_library(command: str, symbol: str) -> None:
    result = runner.invoke(app, ["-"], input=rf"\(A {command} B\)")
    assert result.exit_code == 0, result.output
    assert f"A {symbol} B" in result.output


def test_unknown_command_with_known_prefix_stays_visible() -> None:
    source = r"\[ A \iffunknown B \]"
    result = runner.invoke(app, ["-"], input=source)
    assert result.exit_code == 0, result.output
    assert source in result.output


def test_unicode_math_preserves_unavailable_scripts() -> None:
    source = r"\(\mathcal{S} = \{0, 1\}^*\), \(\mathcal{C}_{phys}\)"
    result = runner.invoke(app, ["-"], input=source)
    assert result.exit_code == 0, result.output
    assert "𝒮 = {0, 1}^*" in result.output
    assert "𝒞_phys" in result.output
