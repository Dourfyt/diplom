#!/usr/bin/env python3
"""IDEF0 модуля ECO → SVG для вставки в Word."""

from __future__ import annotations

from pathlib import Path

OUT_DIR = Path(__file__).resolve().parents[1] / "docs" / "diagrams"

FONT = "Arial, Helvetica, sans-serif"
STROKE = "#1a1a1a"
FILL = "#ffffff"
ACCENT = "#2c5282"

FLOW_SIZE = 13
BOX_SIZE = 14
TITLE_SIZE = 18
SUBTITLE_SIZE = 13
CODE_SIZE = 12
SIDE_SIZE = 11


def _esc(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _header(w: int, h: int, title: str, subtitle: str = "") -> str:
    sub = ""
    if subtitle:
        sub = (
            f'<text x="{w // 2}" y="54" text-anchor="middle" '
            f'font-size="{SUBTITLE_SIZE}" fill="#555">{_esc(subtitle)}</text>'
        )
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">
  <defs>
    <marker id="arrow" markerWidth="9" markerHeight="9" refX="8" refY="4.5" orient="auto">
      <path d="M0,0 L9,4.5 L0,9 z" fill="{STROKE}"/>
    </marker>
    <style>
      text {{ font-family: {FONT}; fill: {STROKE}; }}
    </style>
  </defs>
  <rect width="100%" height="100%" fill="#fafafa"/>
  <text x="{w // 2}" y="32" text-anchor="middle" font-size="{TITLE_SIZE}" font-weight="600">{_esc(title)}</text>
  {sub}
"""


def _footer() -> str:
    return "</svg>\n"


def _multiline(cx: float, cy: float, lines: list[str], size: float, weight: str = "normal") -> str:
    if len(lines) == 1:
        return (
            f'<text x="{cx}" y="{cy}" text-anchor="middle" '
            f'font-size="{size}" font-weight="{weight}">{_esc(lines[0])}</text>'
        )
    lh = size * 1.35
    start = cy - (len(lines) - 1) * lh / 2 + size * 0.35
    return "\n    ".join(
        f'<text x="{cx}" y="{start + i * lh}" text-anchor="middle" '
        f'font-size="{size}" font-weight="{weight}">{_esc(line)}</text>'
        for i, line in enumerate(lines)
    )


def _flow_label(x: float, y: float, text: str, anchor: str = "middle") -> str:
    pad = 4
    fs = FLOW_SIZE
    w = len(text) * fs * 0.52 + pad * 2
    if anchor == "start":
        rx, tx = x - pad, x
    elif anchor == "end":
        rx, tx = x - w + pad, x
    else:
        rx, tx = x - w / 2, x
    return f"""
  <rect x="{rx}" y="{y - fs - 2}" width="{w}" height="{fs + 6}" fill="#fafafa" stroke="none"/>
  <text x="{tx}" y="{y}" text-anchor="{anchor}" font-size="{fs}" fill="#1a1a1a">{_esc(text)}</text>"""


def _arrow(d: str, label: str | None = None, lx: float = 0, ly: float = 0, anchor: str = "middle") -> str:
    parts = [
        f'<path d="{d}" fill="none" stroke="{STROKE}" stroke-width="1.4" marker-end="url(#arrow)"/>'
    ]
    if label:
        parts.append(_flow_label(lx, ly, label, anchor))
    return "\n".join(parts)


def _idef_box(x: float, y: float, w: float, h: float, code: str, lines: list[str], dom: str | None = None) -> str:
    cx, cy = x + w / 2, y + h / 2
    dom_el = ""
    if dom:
        dom_el = (
            f'<text x="{x + w - 8}" y="{y + h - 8}" text-anchor="end" '
            f'font-size="{CODE_SIZE}" fill="#666">{_esc(dom)}</text>'
        )
    return f"""
  <rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{FILL}" stroke="{STROKE}" stroke-width="2"/>
  <text x="{x + 14}" y="{y + 22}" font-size="{CODE_SIZE}" fill="{ACCENT}" font-weight="600">{_esc(code)}</text>
  {_multiline(cx, cy + 4, lines, BOX_SIZE, "600")}
  {dom_el}"""


def _side_label(x: float, y: float, text: str, rotate: float = 0) -> str:
    tr = f' transform="rotate({rotate},{x},{y})"' if rotate else ""
    return (
        f'<text x="{x}" y="{y}" text-anchor="middle" font-size="{SIDE_SIZE}" '
        f'fill="{ACCENT}" font-weight="600"{tr}>{_esc(text)}</text>'
    )


def context_diagram() -> str:
    w, h = 1280, 900
    bx, by, bw, bh = 400, 355, 480, 140
    parts = [_header(w, h, "IDEF0 — контекстная диаграмма A-0", "Веб-модуль отчётности ECO (модель «как есть»)")]

    parts.append(_side_label(28, (by + by + bh) / 2, "ВХОДЫ", -90))
    parts.append(_side_label(w - 28, (by + by + bh) / 2, "ВЫХОДЫ", 90))
    parts.append(_side_label(bx + bw / 2, 72, "УПРАВЛЕНИЕ"))
    parts.append(_side_label(bx + bw / 2, h - 62, "МЕХАНИЗМЫ"))

    parts.append(
        _idef_box(bx, by, bw, bh, "A0", ["Ведение экологической", "отчётности на КПО"])
    )

    # Inputs (left) — ровные горизонтали
    inputs = [
        (by + 28, "Данные партий отходов"),
        (by + 56, "Данные операций движения"),
        (by + 84, "Учётные данные пользователя"),
        (by + 112, "Параметры запросов"),
    ]
    for y_in, lbl in inputs:
        parts.append(_arrow(f"M 48,{y_in} L {bx},{y_in}", lbl, 48, y_in - 7, "start"))

    # Controls (top)
    controls = [
        (bx + 60, "Законодательство об отходах"),
        (bx + 180, "ФККО и нормативы ПДК"),
        (bx + 300, "Ролевая модель доступа"),
        (bx + 420, "Политика работы с API"),
    ]
    for x_c, lbl in controls:
        parts.append(_arrow(f"M {x_c},108 L {x_c},{by}", lbl, x_c, 96))

    # Outputs (right)
    rx = bx + bw
    outputs = [
        (by + 28, "Отчёты PDF / XML"),
        (by + 56, "Дашборды и KPI"),
        (by + 84, "Контроль согласованности"),
        (by + 112, "Записи измерений"),
    ]
    for y_out, lbl in outputs:
        parts.append(_arrow(f"M {rx},{y_out} L {w - 48},{y_out}", lbl, w - 48, y_out - 7, "end"))

    # Mechanisms (bottom) — равномерно по нижней грани
    mechs = [
        (bx + 40, "Администратор"),
        (bx + 136, "Эколог"),
        (bx + 232, "Руководитель"),
        (bx + 328, "Веб-модуль ECO"),
        (bx + 424, "API платформы"),
        (bx + 520, "Смежные модули"),
    ]
    my = by + bh
    for x_m, lbl in mechs:
        parts.append(_arrow(f"M {x_m},{h - 108} L {x_m},{my}", lbl, x_m, h - 122))

    parts.append(
        f'<text x="70" y="{h - 35}" font-size="{FLOW_SIZE}" fill="#666">'
        f"← Вход   ↑ Управление   → Выход   ↓ Механизм</text>"
    )
    parts.append(_footer())
    return "".join(parts)


def decomposition_a0() -> str:
    w, h = 1360, 960
    parts = [
        _header(
            w,
            h,
            "IDEF0 — декомпозиция A0 (уровень 1)",
            "Родитель: A0 — Ведение экологической отчётности на КПО",
        )
    ]

    parts.append(_side_label(32, 480, "ВХОДЫ", -90))
    parts.append(_side_label(w - 32, 480, "ВЫХОДЫ", 90))

    # Control banner
    parts.append(
        f'<text x="{w // 2}" y="92" text-anchor="middle" font-size="{FLOW_SIZE}" fill="#444">'
        f"↑ Управление (с A-0): законодательство · ФККО · роли · политика API</text>"
    )

    bw, bh = 330, 115
    boxes = [
        (90, 130, "A1", ["Аутентификация и", "разграничение доступа"], "1"),
        (540, 130, "A2", ["Администрирование и", "контроль качества данных"], "2"),
        (90, 360, "A3", ["Ведение журнала операций", "и экспорт отчётов"], "3"),
        (540, 360, "A4", ["Учёт экологических", "измерений"], "4"),
        (315, 590, "A5", ["Формирование аналитики", "и KPI"], "5"),
    ]
    for x, y, code, lines, dom in boxes:
        parts.append(_idef_box(x, y, bw, bh, code, lines, dom))

    # External inputs (left boundary)
    parts.append(_arrow("M 42,188 L 90,188", "Учётные данные", 42, 175, "start"))
    parts.append(_arrow("M 42,228 L 540,228", "Данные партий и операций", 42, 215, "start"))
    parts.append(_arrow("M 42,418 L 90,408", "Параметры запросов", 42, 405, "start"))

    # A1 → остальные блоки (сессия)
    parts.append(_arrow("M 420,228 L 540,228", "Сессия и токен", 480, 216))
    parts.append(_arrow("M 255,245 L 255,360", "Сессия", 268, 305, "start"))
    parts.append(_arrow("M 255,475 L 480,590", "Сессия", 350, 540, "start"))
    parts.append(_arrow("M 705,475 L 555,590", "Сессия", 640, 540, "start"))

    # Outputs (right boundary) — на уровне соответствующих блоков
    parts.append(_arrow("M 870,188 L 1318,168", "Сводка целостности", 1318, 155, "end"))
    parts.append(_arrow("M 420,418 L 1318,328", "Файлы отчётов", 1318, 315, "end"))
    parts.append(_arrow("M 870,418 L 1318,408", "Записи измерений", 1318, 395, "end"))
    parts.append(_arrow("M 645,648 L 1318,588", "Дашборды KPI", 1318, 575, "end"))

    parts.append(
        f'<text x="{w // 2}" y="720" text-anchor="middle" font-size="{FLOW_SIZE}" fill="#444">'
        f"↓ Механизмы: веб-модуль ECO · API платформы · пользователи (роли)</text>"
    )
    parts.append(
        f'<text x="80" y="{h - 30}" font-size="{FLOW_SIZE}" fill="#666">'
        f"Цифра в углу блока — порядок доминирования (1 — наибольший)</text>"
    )
    parts.append(_footer())
    return "".join(parts)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "idef0-eco-context.svg").write_text(context_diagram(), encoding="utf-8")
    (OUT_DIR / "idef0-eco-a0.svg").write_text(decomposition_a0(), encoding="utf-8")
    print("Written:", OUT_DIR / "idef0-eco-context.svg")
    print("Written:", OUT_DIR / "idef0-eco-a0.svg")


if __name__ == "__main__":
    main()
