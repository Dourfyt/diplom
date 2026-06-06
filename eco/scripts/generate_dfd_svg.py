#!/usr/bin/env python3
"""DFD модуля ECO (Гейн–Сарсон) → SVG для вставки в Word."""

from __future__ import annotations

from pathlib import Path

OUT_DIR = Path(__file__).resolve().parents[1] / "docs" / "diagrams"

FONT = "Arial, Helvetica, sans-serif"
STROKE = "#1a1a1a"
FILL = "#ffffff"
BOUNDARY = "#4a6fa5"


def _esc(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _header(w: int, h: int, title: str) -> str:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">
  <defs>
    <marker id="arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto">
      <path d="M0,0 L8,4 L0,8 z" fill="{STROKE}"/>
    </marker>
    <style>
      text {{ font-family: {FONT}; fill: {STROKE}; }}
      .title {{ font-size: 15px; font-weight: 600; }}
      .label {{ font-size: 11px; }}
      .flow {{ font-size: 9.5px; fill: #333; }}
      .boundary {{ font-size: 12px; font-weight: 600; fill: {BOUNDARY}; }}
    </style>
  </defs>
  <rect width="100%" height="100%" fill="#fafafa"/>
  <text x="{w // 2}" y="28" text-anchor="middle" class="title">{_esc(title)}</text>
"""


def _footer() -> str:
    return "</svg>\n"


def _multiline(cx: float, cy: float, lines: list[str], size: float = 11, weight: str = "normal") -> str:
    if len(lines) == 1:
        return (
            f'<text x="{cx}" y="{cy}" text-anchor="middle" '
            f'font-size="{size}" font-weight="{weight}">{_esc(lines[0])}</text>'
        )
    lh = size * 1.25
    start = cy - (len(lines) - 1) * lh / 2
    parts = []
    for i, line in enumerate(lines):
        parts.append(
            f'<text x="{cx}" y="{start + i * lh}" text-anchor="middle" '
            f'font-size="{size}" font-weight="{weight}">{_esc(line)}</text>'
        )
    return "\n    ".join(parts)


def entity(x: float, y: float, w: float, h: float, lines: list[str]) -> str:
    cx, cy = x + w / 2, y + h / 2
    return f"""
  <rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{FILL}" stroke="{STROKE}" stroke-width="1.5"/>
  {_multiline(cx, cy, lines)}
"""


def process(cx: float, cy: float, r: float, lines: list[str]) -> str:
    return f"""
  <circle cx="{cx}" cy="{cy}" r="{r}" fill="{FILL}" stroke="{STROKE}" stroke-width="1.5"/>
  {_multiline(cx, cy, lines, size=10)}
"""


def store(x: float, y: float, w: float, h: float, lines: list[str]) -> str:
    """Открытое хранилище Гейна–Сарсона (открыт справа)."""
    cx, cy = x + w / 2, y + h / 2
    gap = 14
    return f"""
  <line x1="{x}" y1="{y}" x2="{x}" y2="{y + h}" stroke="{STROKE}" stroke-width="1.5"/>
  <line x1="{x}" y1="{y}" x2="{x + w - gap}" y2="{y}" stroke="{STROKE}" stroke-width="1.5"/>
  <line x1="{x}" y1="{y + h}" x2="{x + w - gap}" y2="{y + h}" stroke="{STROKE}" stroke-width="1.5"/>
  {_multiline(cx, cy, lines, size=10)}
"""


def boundary(x: float, y: float, w: float, h: float, label: str) -> str:
    return f"""
  <rect x="{x}" y="{y}" width="{w}" height="{h}" fill="none" stroke="{BOUNDARY}"
        stroke-width="1.5" stroke-dasharray="8 5" rx="4"/>
  <text x="{x + 12}" y="{y + 20}" class="boundary">{_esc(label)}</text>
"""


def arrow(
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    label: str = "",
    *,
    mid: tuple[float, float] | None = None,
    label_dx: float = 0,
    label_dy: float = 0,
) -> str:
    if mid:
        mx, my = mid
        d = f"M{x1},{y1} L{mx},{my} L{x2},{y2}"
        lx, ly = mx + label_dx, my + label_dy
    else:
        d = f"M{x1},{y1} L{x2},{y2}"
        lx, ly = (x1 + x2) / 2 + label_dx, (y1 + y2) / 2 + label_dy
    parts = [
        f'<path d="{d}" fill="none" stroke="{STROKE}" stroke-width="1.1" '
        f'marker-end="url(#arrow)"/>'
    ]
    if label:
        parts.append(
            f'<text x="{lx}" y="{ly}" text-anchor="middle" class="flow">{_esc(label)}</text>'
        )
    return "\n".join(parts)


def build_level0_svg() -> str:
    w, h = 920, 340
    parts = [_header(w, h, "DFD уровня 0 — веб-модуль отчётности ECO (контекст)")]
    # Позиции
    e1 = (60, 155, 130, 58)
    p0 = (310, 145, 180, 78)
    e2 = (610, 150, 160, 68)
    parts.append(entity(*e1, ["1", "Пользователь"]))
    parts.append(process(400, 184, 52, ["0", "Веб-модуль", "отчётности ECO"]))
    parts.append(entity(*e2, ["2", "API-платформа"]))
    parts.append(arrow(190, 184, 348, 184, "запросы, параметры", label_dy=-8))
    parts.append(arrow(452, 184, 610, 184, "отчёты, файлы", label_dy=10))
    parts.append(arrow(452, 168, 610, 168, "запросы REST API", label_dy=-10))
    parts.append(arrow(610, 200, 452, 200, "данные платформы", label_dy=12))
    parts.append(_footer())
    return "".join(parts)


def build_level1_svg() -> str:
    w, h = 1180, 720
    parts = [_header(w, h, "DFD уровня 1 — веб-модуль отчётности ECO (нотация Гейна–Сарсона)")]

    # Граница системы ECO
    bx, by, bw, bh = 175, 95, 720, 520
    parts.append(boundary(bx, by, bw, bh, "ECO — веб-модуль отчётности"))

    # Внешние сущности
    parts.append(entity(30, 300, 118, 62, ["1", "Пользователь"]))
    parts.append(entity(470, 38, 138, 58, ["2", "API-платформа"]))

    # Процессы (круги)
    r = 48
    p1 = (280, 340)
    p2 = (480, 300)
    p3 = (680, 300)
    p4 = (480, 480)
    p5 = (680, 480)
    parts.append(process(*p1, r, ["1.0", "Аутентифицировать", "пользователя"]))
    parts.append(process(*p2, r, ["2.0", "Сформировать", "дашборд и журнал"]))
    parts.append(process(*p3, r, ["3.0", "Сформировать", "файл экспорта"]))
    parts.append(process(*p4, r, ["4.0", "Проверить", "согласованность"]))
    parts.append(process(*p5, r, ["5.0", "Зарегистрировать", "измерение"]))

    # D1 — между p1 и p2
    parts.append(store(355, 195, 100, 48, ["D1", "Сессия"]))

    # Потоки: пользователь → процессы
    ux, uy = 148, 331
    parts.append(arrow(ux, uy, p1[0] - r, p1[1], "email, пароль", label_dy=-10))
    parts.append(arrow(ux, 318, p2[0] - r, p2[1] - 10, "период, фильтры", mid=(220, 260), label_dx=0, label_dy=-8))
    parts.append(arrow(ux, 345, p3[0] - r, p3[1] - 5, "формат, фильтры", mid=(200, 200), label_dx=-15, label_dy=-6))
    parts.append(arrow(ux, 358, p4[0] - r, p4[1], "критерии контроля", mid=(210, 420), label_dx=-20, label_dy=0))
    parts.append(arrow(ux, 370, p5[0] - r, p5[1], "параметры измерения", mid=(200, 540), label_dx=-25, label_dy=4))

    # Пользователь ← результаты
    parts.append(arrow(p1[0] - r + 10, p1[1] + 15, ux, uy + 25, "уведомление о входе", label_dy=12))
    parts.append(arrow(p2[0] - r, p2[1] + 20, ux, 340, "журнал, графики", mid=(200, 380), label_dy=8))
    parts.append(arrow(p3[0] - r, p3[1] + 25, ux, 352, "pdf / xml", mid=(180, 450), label_dy=6))
    parts.append(arrow(p4[0] - r, p4[1], ux, 365, "панель проблем", mid=(170, 500), label_dy=4))
    parts.append(arrow(p5[0] - r, p5[1], ux, 378, "подтверждение", mid=(170, 560), label_dy=4))

    # API (верх)
    ax, ay = 539, 96
    parts.append(arrow(p1[0], p1[1] - r, ax, ay + 58, "запрос аутентификации", label_dx=20, label_dy=-6))
    parts.append(arrow(ax, ay + 58, p1[0] + 15, p1[1] - r, "токен, профиль", label_dx=25, label_dy=8))
    parts.append(arrow(p2[0], p2[1] - r, ax + 30, ay + 58, "запрос KPI", label_dx=0, label_dy=-8))
    parts.append(arrow(ax + 40, ay + 58, p2[0] + 10, p2[1] - r, "операции, KPI", label_dx=10, label_dy=6))
    parts.append(arrow(p3[0], p3[1] - r, ax + 60, ay + 58, "запрос для отчёта", label_dx=15, label_dy=-8))
    parts.append(arrow(ax + 70, ay + 58, p3[0], p3[1] - r, "данные экспорта", label_dx=20, label_dy=6))
    parts.append(arrow(p4[0], p4[1] - r, ax - 20, ay + 58, "запрос проверки", label_dx=-15, label_dy=-8))
    parts.append(arrow(ax - 10, ay + 58, p4[0], p4[1] - r, "наборы severity", label_dx=-5, label_dy=6))
    parts.append(arrow(p5[0], p5[1] - r, ax + 90, ay + 58, "справочники, запись", label_dx=30, label_dy=-8))
    parts.append(arrow(ax + 100, ay + 58, p5[0] + 5, p5[1] - r, "статус записи", label_dx=35, label_dy=6))

    # D1
    sx, sy = 405, 219
    parts.append(arrow(p1[0] + 20, p1[1] - 35, sx, sy + 48, "данные сессии", label_dx=12, label_dy=-6))
    parts.append(arrow(sx + 50, sy, p2[0] - 25, p2[1] - 35, "токен, роль", label_dy=-8))
    parts.append(arrow(sx + 70, sy + 10, p3[0] - 40, p3[1] - 40, "токен, роль", label_dx=15, label_dy=-6))
    parts.append(arrow(sx + 30, sy + 48, p4[0] - 30, p4[1] - 45, "токен, роль", label_dx=-10, label_dy=4))
    parts.append(arrow(sx + 80, sy + 48, p5[0] - 35, p5[1] - 45, "токен, роль", label_dx=20, label_dy=4))

    parts.append(_footer())
    return "".join(parts)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    files = {
        "dfd-eco-level0.svg": build_level0_svg(),
        "dfd-eco-level1.svg": build_level1_svg(),
    }
    for name, content in files.items():
        path = OUT_DIR / name
        path.write_text(content, encoding="utf-8")
        print("Wrote", path)


if __name__ == "__main__":
    main()
