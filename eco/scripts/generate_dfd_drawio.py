#!/usr/bin/env python3
"""
DFD модуля ECO (нотация Гейна–Сарсона) → draw.io.

Проверка по типичным ошибкам DFD:
- один уровень абстракции на диаграмме;
- нет потоков «хранилище ↔ хранилище» и «сущность ↔ сущность»;
- удалённые БД API не показаны как внутренние хранилища ECO;
- процессы с глаголами, потоки подписаны.
"""

from __future__ import annotations

from pathlib import Path

OUT_DIR = Path(__file__).resolve().parents[1] / "docs" / "diagrams"

S_ENTITY = (
    "rounded=0;whiteSpace=wrap;html=1;align=center;verticalAlign=middle;"
    "fillColor=#ffffff;strokeColor=#000000;fontSize=12;"
)
S_PROCESS = (
    "ellipse;whiteSpace=wrap;html=1;aspect=fixed;align=center;verticalAlign=middle;"
    "fillColor=#ffffff;strokeColor=#000000;fontSize=11;"
)
S_BOUNDARY = (
    "rounded=0;dashed=1;dashPattern=8 6;strokeColor=#4a6fa5;strokeWidth=2;"
    "fillColor=none;align=left;verticalAlign=top;spacingLeft=8;spacingTop=6;"
    "fontColor=#4a6fa5;fontStyle=1;fontSize=12;"
)
S_STORE = (
    "shape=partialRectangle;whiteSpace=wrap;html=1;bottom=0;right=0;"
    "fillColor=none;strokeColor=#000000;align=left;spacingLeft=6;"
    "verticalAlign=middle;fontSize=12;"
)
S_EDGE = (
    "edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;"
    "jettySize=auto;html=1;fontSize=11;strokeColor=#000000;"
)


def esc(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def cell(cid: str, value: str, x: int, y: int, w: int, h: int, style: str) -> str:
    return (
        f'        <mxCell id="{cid}" value="{esc(value)}" style="{style}" '
        f'vertex="1" parent="1">\n'
        f'          <mxGeometry x="{x}" y="{y}" width="{w}" height="{h}" as="geometry" />\n'
        f"        </mxCell>"
    )


def boundary(cid: str, label: str, x: int, y: int, w: int, h: int) -> str:
    return cell(cid, label, x, y, w, h, S_BOUNDARY)


def edge(eid: str, src: str, tgt: str, label: str = "") -> str:
    lbl = f' value="{esc(label)}"' if label else ""
    return (
        f'        <mxCell id="{eid}" style="{S_EDGE}" edge="1" parent="1" '
        f'source="{src}" target="{tgt}"{lbl}>\n'
        f'          <mxGeometry relative="1" as="geometry" />\n'
        f"        </mxCell>"
    )


def wrap_mxfile(diagram_id: str, diagram_name: str, body: str, page_w: int = 1169) -> str:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<mxfile host="eco-diplom" modified="2026-06-02T00:00:00.000Z" agent="generate_dfd_drawio" version="22.1.0" type="device">
  <diagram id="{diagram_id}" name="{esc(diagram_name)}">
    <mxGraphModel dx="1200" dy="800" grid="1" gridSize="10" guides="1" tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" pageWidth="{page_w}" pageHeight="827" math="0" shadow="0">
      <root>
        <mxCell id="0" />
        <mxCell id="1" parent="0" />
{body}
      </root>
    </mxGraphModel>
  </diagram>
</mxfile>
"""


def build_level0() -> str:
    """Контекстная DFD (уровень 0): одна система — веб-модуль ECO."""
    cells = [
        cell("e1", "1\nПользователь", 80, 200, 130, 70, S_ENTITY),
        cell("p0", "0\nВеб-модуль\nотчётности ECO", 370, 175, 110, 110, S_PROCESS),
        cell("e2", "2\nAPI-платформа\n(БД waste_complex)", 680, 200, 150, 80, S_ENTITY),
    ]
    edges = [
        edge("f01", "e1", "p0", "запросы пользователя, параметры"),
        edge("f02", "p0", "e1", "отчёты, панели, файлы, подтверждения"),
        edge("f03", "p0", "e2", "запросы к REST API"),
        edge("f04", "e2", "p0", "данные платформы, статусы операций"),
    ]
    return wrap_mxfile("dfd-eco-l0", "DFD ECO Level 0", "\n".join(cells + edges), 980)


def build_level1() -> str:
    """
    DFD уровня 1: граница системы = ECO.
    Единственное внутреннее хранилище — локальная сессия (D1).
    Данные платформы — только через внешнюю сущность API (не «чёрные» хранилища).
    """
    cells = [
        boundary("sys", "ECO — веб-модуль отчётности", 165, 95, 720, 520),
        cell("e1", "1\nПользователь", 35, 295, 115, 65, S_ENTITY),
        cell("e2", "2\nAPI-платформа", 465, 35, 130, 60, S_ENTITY),
        cell("p1", "1.0\nАутентифицировать\nпользователя", 215, 285, 100, 100, S_PROCESS),
        cell("p2", "2.0\nСформировать\nдашборд и журнал", 415, 245, 100, 100, S_PROCESS),
        cell("p3", "3.0\nСформировать\nфайл экспорта", 615, 245, 100, 100, S_PROCESS),
        cell("p4", "4.0\nПроверить\nсогласованность", 415, 425, 100, 100, S_PROCESS),
        cell("p5", "5.0\nЗарегистрировать\nизмерение", 615, 425, 100, 100, S_PROCESS),
        cell("d1", "D1\nСессия", 355, 185, 95, 48, S_STORE),
    ]
    edges = [
        # П.1 Аутентификация
        edge("f01", "e1", "p1", "email, пароль"),
        edge("f02", "p1", "e2", "запрос аутентификации"),
        edge("f03", "e2", "p1", "токен, профиль пользователя"),
        edge("f04", "p1", "d1", "данные сессии"),
        edge("f05", "p1", "e1", "уведомление об успешном входе"),
        # Контекст доступа к остальным процессам
        edge("f06", "d1", "p2", "токен, роль"),
        edge("f07", "d1", "p3", "токен, роль"),
        edge("f08", "d1", "p4", "токен, роль"),
        edge("f09", "d1", "p5", "токен, роль"),
        # П.2 Дашборд и журнал
        edge("f10", "e1", "p2", "период, фильтры журнала"),
        edge("f11", "p2", "e2", "запрос операций и KPI"),
        edge("f12", "e2", "p2", "список операций, агрегаты KPI"),
        edge("f13", "p2", "e1", "таблица журнала, графики"),
        # П.3 Экспорт
        edge("f14", "e1", "p3", "формат файла, фильтры"),
        edge("f15", "p3", "e2", "запрос набора для отчёта"),
        edge("f16", "e2", "p3", "данные для экспорта"),
        edge("f17", "p3", "e1", "файл pdf / xml"),
        # П.4 Контроль данных
        edge("f18", "e1", "p4", "критерии контроля"),
        edge("f19", "p4", "e2", "запрос организаций, партий, операций"),
        edge("f20", "e2", "p4", "наборы для проверки severity"),
        edge("f21", "p4", "e1", "панель проблем и предупреждений"),
        # П.5 Измерение
        edge("f22", "e1", "p5", "параметры нового измерения"),
        edge("f23", "p5", "e2", "запрос справочников и сохранение"),
        edge("f24", "e2", "p5", "списки организаций, статус записи"),
        edge("f25", "p5", "e1", "подтверждение регистрации"),
    ]
    return wrap_mxfile("dfd-eco-l1", "DFD ECO Level 1", "\n".join(cells + edges), 1280)


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    files = {
        "dfd-eco-level0.drawio": build_level0(),
        "dfd-eco.drawio": build_level1(),
    }
    for name, content in files.items():
        path = OUT_DIR / name
        path.write_text(content, encoding="utf-8")
        print("Wrote", path)


if __name__ == "__main__":
    main()
