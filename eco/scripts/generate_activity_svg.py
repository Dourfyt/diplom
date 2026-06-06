#!/usr/bin/env python3
"""UML Activity диаграммы ECO → SVG (локальная генерация, без сети)."""

from __future__ import annotations

from pathlib import Path

OUT_DIR = Path(__file__).resolve().parents[1] / "docs" / "diagrams"
FONT = "Arial, Helvetica, sans-serif"
STROKE = "#1a1a1a"
LANE_FILL = "#f7fafc"
LANE_STROKE = "#2c5282"
ACTION_FILL = "#ffffff"


def _esc(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _svg_header(w: int, h: int, title: str, subtitle: str = "") -> str:
    sub = ""
    if subtitle:
        sub = (
            f'<text x="{w // 2}" y="52" text-anchor="middle" '
            f'font-size="12" fill="#555" font-family="{FONT}">'
            f"{_esc(subtitle)}</text>"
        )
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">
  <rect width="100%" height="100%" fill="#fff"/>
  <text x="{w // 2}" y="28" text-anchor="middle" font-size="16" font-weight="600"
        font-family="{FONT}">{_esc(title)}</text>
  {sub}
"""


def _lane(x: int, y: int, w: int, h: int, label: str) -> str:
    lx = x + w // 2
    return f"""
  <rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{LANE_FILL}" stroke="{LANE_STROKE}" stroke-width="1.5"/>
  <text x="{lx}" y="{y + 22}" text-anchor="middle" font-size="11" font-weight="600"
        font-family="{FONT}" fill="{LANE_STROKE}">{_esc(label)}</text>
"""


def _action(cx: int, cy: int, text: str, aw: int = 168, ah: int = 44) -> str:
    x, y = cx - aw // 2, cy - ah // 2
    lines = text.split("\n")
    tspans = "".join(
        f'<tspan x="{cx}" dy="{14 if i else 0}">{_esc(line)}</tspan>'
        for i, line in enumerate(lines)
    )
    return f"""
  <rect x="{x}" y="{y}" width="{aw}" height="{ah}" rx="10" ry="10"
        fill="{ACTION_FILL}" stroke="{STROKE}" stroke-width="1.5"/>
  <text text-anchor="middle" font-size="11" font-family="{FONT}" fill="{STROKE}">
    <text x="{cx}" y="{cy - 6 + (len(lines) - 1) * -6}">{tspans}</text>
  </text>
"""


def _arrow(x1: int, y1: int, x2: int, y2: int) -> str:
    return f"""
  <line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{STROKE}" stroke-width="1.5"
        marker-end="url(#arrow)"/>
"""


def _fork_join(cx: int, y: int, w: int) -> str:
    x1, x2 = cx - w // 2, cx + w // 2
    return f'<line x1="{x1}" y1="{y}" x2="{x2}" y2="{y}" stroke="{STROKE}" stroke-width="5"/>'


def _start(cx: int, cy: int) -> str:
    return f'<circle cx="{cx}" cy="{cy}" r="10" fill="{STROKE}"/>'


def _end(cx: int, cy: int) -> str:
    return f"""
  <circle cx="{cx}" cy="{cy}" r="14" fill="none" stroke="{STROKE}" stroke-width="2"/>
  <circle cx="{cx}" cy="{cy}" r="8" fill="{STROKE}"/>
"""


def _defs() -> str:
    return """
  <defs>
    <marker id="arrow" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto">
      <path d="M0,0 L6,3 L0,6 Z" fill="#1a1a1a"/>
    </marker>
  </defs>
"""


def eco_p14_export() -> str:
    w, h = 920, 860
    top, lane_h = 70, 790
    col_w = w // 3
    xs = [col_w // 2, col_w + col_w // 2, 2 * col_w + col_w // 2]
    lanes = [
        "Эколог",
        "Веб-модуль ECO",
        "API платформы",
    ]
    parts = [_svg_header(w, h, "UML Activity — экспорт журнала операций (P-14)",
                         "Веб-модуль отчётности ECO"), _defs()]
    for i, name in enumerate(lanes):
        parts.append(_lane(i * col_w, top, col_w, lane_h, name))

    y0 = top + 55
    dy = 78
    y = y0
    parts.append(_start(xs[0], y))
    y += 28
    parts.append(_arrow(xs[0], y - 18, xs[0], y))
    actions_eco = [
        (0, "Открыть журнал\nопераций"),
        (0, "Задать фильтры\n(организация, период)"),
        (0, "Запросить экспорт"),
        (0, "Выбрать формат\n(PDF / XML)"),
    ]
    for lane, text in actions_eco:
        parts.append(_action(xs[lane], y, text))
        y += dy
        parts.append(_arrow(xs[lane], y - dy + 22, xs[lane], y - 14))

    fork_y = y - 10
    parts.append(_fork_join(w // 2, fork_y, col_w * 2 + 40))
    y_fork = fork_y + 35
    parts.append(_action(xs[1], y_fork, "Подготовить шаблон\nPDF или XML"))
    parts.append(_action(xs[2], y_fork, "Получить операции\nдвижения за период"))
    parts.append(_arrow(xs[0], y - 14, w // 2, fork_y))
    parts.append(_arrow(w // 2, fork_y, xs[1], y_fork - 22))
    parts.append(_arrow(w // 2, fork_y, xs[2], y_fork - 22))

    join_y = y_fork + 72
    parts.append(_fork_join(w // 2, join_y, col_w * 2 + 40))
    parts.append(_arrow(xs[1], y_fork + 22, xs[1], join_y))
    parts.append(_arrow(xs[2], y_fork + 22, xs[2], join_y))
    parts.append(_arrow(xs[1], join_y, xs[1], join_y + 28))
    parts.append(_arrow(xs[2], join_y, xs[2], join_y + 28))

    y_merge = join_y + 55
    parts.append(
        _action(
            xs[1],
            y_merge,
            "Объединить данные\nи сформировать файл\n(PDF / XML)",
            ah=58,
        )
    )
    parts.append(_arrow(w // 2, join_y, xs[1], y_merge - 22))

    y_dl = y_merge + dy
    parts.append(_action(xs[0], y_dl, "Скачать отчёт"))
    parts.append(_arrow(xs[1], y_merge + 22, xs[0], y_dl - 22))

    y_end = y_dl + 50
    parts.append(_end(xs[0], y_end))
    parts.append(_arrow(xs[0], y_dl + 22, xs[0], y_end - 16))
    parts.append("</svg>")
    return "".join(parts)


def example_trading() -> str:
    w, h = 900, 820
    top, lane_h = 70, 750
    col_w = w // 3
    xs = [col_w // 2, col_w + col_w // 2, 2 * col_w + col_w // 2]
    lanes = [
        "Отдел приёма и\nоформления заказов",
        "Отдел продаж",
        "Склад",
    ]
    parts = [_svg_header(w, h, "Фрагмент диаграммы действий",
                         "Пример: торговая компания (дорожки + fork/join)"), _defs()]
    for i, name in enumerate(lanes):
        parts.append(_lane(i * col_w, top, col_w, lane_h, name))

    y = top + 55
    dy = 72
    parts.append(_start(xs[0], y))
    y += 28
    parts.append(_arrow(xs[0], y - 18, xs[0], y))
    parts.append(_action(xs[0], y, "Принять заказ на товар"))
    y += dy
    parts.append(_arrow(xs[0], y - dy + 22, xs[0], y - 14))

    fork_y = y
    parts.append(_fork_join(w // 2, fork_y, col_w * 2 + 40))
    y_p = fork_y + 40
    parts.append(_action(xs[0], y_p, "Получить оплату\nза товар"))
    parts.append(_action(xs[1], y_p, "Зарегистрировать заказ"))
    parts.append(_arrow(xs[0], y - 14, w // 2, fork_y))
    parts.append(_arrow(w // 2, fork_y, xs[0], y_p - 22))
    parts.append(_arrow(w // 2, fork_y, xs[1], y_p - 22))

    join_y = y_p + 78
    parts.append(_fork_join(w // 2, join_y, col_w * 2 + 40))
    parts.append(_arrow(xs[0], y_p + 22, xs[0], join_y))
    parts.append(_arrow(xs[1], y_p + 22, xs[1], join_y))

    y_wh = join_y + 55
    for text in ("Отпустить товар", "Подготовить товар\nк отправке", "Отправить товар\nклиенту"):
        parts.append(_action(xs[2], y_wh, text))
        if text != "Отправить товар\nклиенту":
            parts.append(_arrow(xs[2], y_wh + 22, xs[2], y_wh + dy - 14))
        y_wh += dy
    parts.append(_arrow(w // 2, join_y, xs[2], join_y + 28))

    y_close = y_wh + 20
    parts.append(_action(xs[0], y_close, "Закрыть заказ"))
    parts.append(_arrow(xs[2], y_wh - 14, xs[0], y_close - 22))

    y_end = y_close + 52
    parts.append(_end(xs[0], y_end))
    parts.append(_arrow(xs[0], y_close + 22, xs[0], y_end - 16))
    parts.append("</svg>")
    return "".join(parts)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "activity-eco-p14-export.svg").write_text(
        eco_p14_export(), encoding="utf-8"
    )
    (OUT_DIR / "activity-example-trading.svg").write_text(
        example_trading(), encoding="utf-8"
    )
    print("OK docs/diagrams/activity-eco-p14-export.svg")
    print("OK docs/diagrams/activity-example-trading.svg")


if __name__ == "__main__":
    main()
