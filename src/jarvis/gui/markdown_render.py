"""Лёгкий рендер Markdown -> HTML (подмножество Qt RichText) с темой Jarvis.

Без внешних зависимостей. Поддержка: заголовки, **жирный**, *курсив*,
`код`, блоки ```код```, списки (- и 1.), ссылки, переносы строк.
Цвета берутся из палитры темы (кибербез-терминал).
"""
from __future__ import annotations

import html
import re

from jarvis.gui.theme import Colors

_MONO = "Consolas, 'JetBrains Mono', monospace"


def _inline(text: str) -> str:
    """Инлайновое форматирование внутри уже экранированной строки."""
    # `код`
    text = re.sub(
        r"`([^`]+)`",
        rf'<code style="background:{Colors.BG_DARKEST};color:{Colors.ACCENT};'
        rf'font-family:{_MONO};padding:1px 4px;border-radius:3px;">\1</code>',
        text,
    )
    # **жирный**
    text = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", text)
    # *курсив*
    text = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<i>\1</i>", text)
    # [текст](ссылка)
    text = re.sub(
        r"\[([^\]]+)\]\((https?://[^)]+)\)",
        rf'<a href="\2" style="color:{Colors.ACCENT_GLOW};">\1</a>',
        text,
    )
    return text


def markdown_to_html(md: str) -> str:
    """Конвертирует Markdown в HTML для QLabel (Qt RichText)."""
    lines = md.split("\n")
    out: list[str] = []
    i = 0
    in_ul = False
    in_ol = False

    def close_lists() -> None:
        nonlocal in_ul, in_ol
        if in_ul:
            out.append("</ul>")
            in_ul = False
        if in_ol:
            out.append("</ol>")
            in_ol = False

    while i < len(lines):
        line = lines[i]

        # блок кода ```
        if line.strip().startswith("```"):
            close_lists()
            i += 1
            code_lines: list[str] = []
            while i < len(lines) and not lines[i].strip().startswith("```"):
                code_lines.append(html.escape(lines[i]))
                i += 1
            i += 1  # пропускаем закрывающие ```
            code = "<br>".join(code_lines)
            out.append(
                f'<pre style="background:{Colors.BG_DARKEST};color:{Colors.TEXT_PRIMARY};'
                f'font-family:{_MONO};padding:10px 12px;border-radius:6px;'
                f'border:1px solid {Colors.ACCENT_DARK};white-space:pre-wrap;">{code}</pre>'
            )
            continue

        raw = line.strip()
        esc = _inline(html.escape(line))

        # заголовки
        m = re.match(r"^(#{1,6})\s+(.*)$", raw)
        if m:
            close_lists()
            level = len(m.group(1))
            size = {1: 18, 2: 16, 3: 15}.get(level, 14)
            out.append(
                f'<div style="color:{Colors.ACCENT};font-weight:700;font-size:{size}px;'
                f'margin:6px 0 2px 0;">{_inline(html.escape(m.group(2)))}</div>'
            )
            i += 1
            continue

        # маркированный список
        m = re.match(r"^[-*]\s+(.*)$", raw)
        if m:
            if not in_ul:
                close_lists()
                out.append(f'<ul style="margin:2px 0 2px 18px;">')
                in_ul = True
            out.append(f"<li>{_inline(html.escape(m.group(1)))}</li>")
            i += 1
            continue

        # нумерованный список
        m = re.match(r"^\d+\.\s+(.*)$", raw)
        if m:
            if not in_ol:
                close_lists()
                out.append(f'<ol style="margin:2px 0 2px 18px;">')
                in_ol = True
            out.append(f"<li>{_inline(html.escape(m.group(1)))}</li>")
            i += 1
            continue

        # пустая строка
        if not raw:
            close_lists()
            out.append("<div style='height:6px;'></div>")
            i += 1
            continue

        # обычный абзац
        close_lists()
        out.append(f"<div>{esc}</div>")
        i += 1

    close_lists()
    return "".join(out)
