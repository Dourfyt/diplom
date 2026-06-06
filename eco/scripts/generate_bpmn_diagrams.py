#!/usr/bin/env python3
"""
Генерация BPMN 2.0 по алгоритму docs/diagrams/bpm/BPMN_GOST_ALGORITHM.md.

Четыре основных сквозных процесса (не по ролям):
  P-01 — аутентификация
  P-08 — контроль качества данных
  P-14 — просмотр и экспорт журнала операций
  P-17 — создание экологического измерения
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

OUT = Path(__file__).resolve().parents[1] / "docs" / "diagrams" / "bpm"

NS = (
    'xmlns:bpmn="http://www.omg.org/spec/BPMN/20100524/MODEL" '
    'xmlns:bpmndi="http://www.omg.org/spec/BPMN/20100524/DI" '
    'xmlns:dc="http://www.omg.org/spec/DD/20100524/DC" '
    'xmlns:di="http://www.omg.org/spec/DD/20100524/DC" '
    'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"'
)

ORIGIN_X = 140
DX = 152
Y_USER = 108
Y_ECO = 248
Y_API = 388
TASK_W = 118
TASK_H = 64
GW = 46


def esc(s: str) -> str:
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


@dataclass(frozen=True)
class Node:
    id: str
    name: str
    lane: str  # user | eco | api
    kind: str  # start | end | end_err | user | service | xor
    col: int


@dataclass(frozen=True)
class Flow:
    id: str
    src: str
    tgt: str
    label: str | None = None


def x_at(col: int) -> int:
    return ORIGIN_X + col * DX


def place(lane: str, col: int, kind: str) -> tuple[int, int, int, int, bool]:
    if kind in ("start", "end", "end_err"):
        w, h, gw = 36, 36, False
        y = Y_USER - 18 if lane == "user" else Y_ECO - 18
        if kind == "end_err":
            y = Y_USER - 18
        return (x_at(col), y, w, h, gw)
    if kind == "xor":
        w, h, gw = GW, GW, True
    else:
        w, h, gw = TASK_W, TASK_H, False
    y = {"user": Y_USER, "eco": Y_ECO, "api": Y_API}[lane] - h // 2
    x = x_at(col) + (TASK_W - w) // 2
    return (x, y, w, h, gw)


def bounds(layout: dict, eid: str) -> tuple[int, int, int, int]:
    x, y, w, h, _ = layout[eid]
    return x, y, w, h


def port_right(eid: str, layout: dict) -> tuple[int, int]:
    x, y, w, h = bounds(layout, eid)
    return x + w, y + h // 2


def port_left(eid: str, layout: dict) -> tuple[int, int]:
    x, y, w, h = bounds(layout, eid)
    return x, y + h // 2


def port_bottom(eid: str, layout: dict) -> tuple[int, int]:
    x, y, w, h = bounds(layout, eid)
    return x + w // 2, y + h


def port_top(eid: str, layout: dict) -> tuple[int, int]:
    x, y, w, h = bounds(layout, eid)
    return x + w // 2, y


def route_lr(src: str, tgt: str, layout: dict) -> list[tuple[int, int]]:
    p1 = port_right(src, layout)
    p4 = port_left(tgt, layout)
    if abs(p1[1] - p4[1]) < 18:
        return [p1, p4]
    mid_x = p1[0] + max(24, (p4[0] - p1[0]) // 2)
    return [p1, (mid_x, p1[1]), (mid_x, p4[1]), p4]


def route_down(src: str, tgt: str, layout: dict) -> list[tuple[int, int]]:
    p1 = port_bottom(src, layout)
    p4 = port_top(tgt, layout)
    if abs(p1[0] - p4[0]) < 18:
        return [p1, p4]
    mid_y = (p1[1] + p4[1]) // 2
    return [p1, (p1[0], mid_y), (p4[0], mid_y), p4]


def route_edge(src: str, tgt: str, layout: dict) -> list[tuple[int, int]]:
    sy = bounds(layout, src)[1]
    ty = bounds(layout, tgt)[1]
    if ty - sy > 70:
        return route_down(src, tgt, layout)
    return route_lr(src, tgt, layout)


def node_bpmn(n: Node, incoming: list[str], outgoing: list[str]) -> str:
    inc = "\n".join(f'      <bpmn:incoming>{f}</bpmn:incoming>' for f in incoming)
    out = "\n".join(f'      <bpmn:outgoing>{f}</bpmn:outgoing>' for f in outgoing)
    tag = {
        "start": "startEvent",
        "end": "endEvent",
        "end_err": "endEvent",
        "user": "userTask",
        "service": "serviceTask",
        "xor": "exclusiveGateway",
    }[n.kind]
    return (
        f'    <bpmn:{tag} id="{n.id}" name="{esc(n.name)}">\n'
        f"{inc}\n{out}\n"
        f"    </bpmn:{tag}>"
    )


def build_process(
    file_id: str,
    title: str,
    nodes: list[Node],
    flows: list[Flow],
) -> str:
    by_id = {n.id: n for n in nodes}
    inc_map: dict[str, list[str]] = {n.id: [] for n in nodes}
    out_map: dict[str, list[str]] = {n.id: [] for n in nodes}
    for f in flows:
        out_map[f.src].append(f.id)
        inc_map[f.tgt].append(f.id)

    layout = {n.id: place(n.lane, n.col, n.kind) for n in nodes}
    max_col = max(n.col for n in nodes)
    width = x_at(max_col + 1) + TASK_W + 60

    lane_refs = {
        "user": [n.id for n in nodes if n.lane == "user"],
        "eco": [n.id for n in nodes if n.lane == "eco"],
        "api": [n.id for n in nodes if n.lane == "api"],
    }
    lane_names = {
        "user": "Пользователь",
        "eco": "Веб-модуль ECO",
        "api": "API платформы",
    }

    lane_xml = ["    <bpmn:laneSet>"]
    for lid, key in [("lane_user", "user"), ("lane_eco", "eco"), ("lane_api", "api")]:
        lane_xml.append(f'      <bpmn:lane id="{lid}" name="{esc(lane_names[key])}">')
        for ref in lane_refs[key]:
            lane_xml.append(f"        <bpmn:flowNodeRef>{ref}</bpmn:flowNodeRef>")
        lane_xml.append("      </bpmn:lane>")
    lane_xml.append("    </bpmn:laneSet>")

    node_xml = "\n".join(
        node_bpmn(by_id[nid], inc_map[nid], out_map[nid]) for nid in by_id
    )
    flow_xml = "\n".join(
        f'    <bpmn:sequenceFlow id="{f.id}" sourceRef="{f.src}" targetRef="{f.tgt}"'
        + (f' name="{esc(f.label)}">' if f.label else ">")
        + f"\n    </bpmn:sequenceFlow>"
        for f in flows
    )

    lane_shapes = [
        f'      <bpmndi:BPMNShape id="lane_user_di" bpmnElement="lane_user" isHorizontal="true">\n'
        f'        <dc:Bounds x="80" y="52" width="{width}" height="142" />\n'
        f"      </bpmndi:BPMNShape>",
        f'      <bpmndi:BPMNShape id="lane_eco_di" bpmnElement="lane_eco" isHorizontal="true">\n'
        f'        <dc:Bounds x="80" y="194" width="{width}" height="142" />\n'
        f"      </bpmndi:BPMNShape>",
        f'      <bpmndi:BPMNShape id="lane_api_di" bpmnElement="lane_api" isHorizontal="true">\n'
        f'        <dc:Bounds x="80" y="336" width="{width}" height="142" />\n'
        f"      </bpmndi:BPMNShape>",
    ]
    shapes = lane_shapes + [
        "      <bpmndi:BPMNShape "
        f'id="{n.id}_di" bpmnElement="{n.id}"'
        + (' isMarkerVisible="true"' if n.kind == "xor" else "")
        + f">\n        <dc:Bounds x=\"{layout[n.id][0]}\" y=\"{layout[n.id][1]}\" "
        f'width="{layout[n.id][2]}" height="{layout[n.id][3]}" />\n'
        f"      </bpmndi:BPMNShape>"
        for n in nodes
    ]
    edges = []
    for f in flows:
        pts = route_edge(f.src, f.tgt, layout)
        wps = "\n".join(f'        <di:waypoint x="{x}" y="{y}" />' for x, y in pts)
        edges.append(
            f'      <bpmndi:BPMNEdge id="{f.id}_di" bpmnElement="{f.id}">\n{wps}\n      </bpmndi:BPMNEdge>'
        )

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<bpmn:definitions {NS} id="Definitions_{file_id}" targetNamespace="http://bpmn.io/schema/bpmn" exporter="eco-diplom" exporterVersion="3.0">
  <bpmn:process id="Process_{file_id}" name="{esc(title)}" isExecutable="false">
{chr(10).join(lane_xml)}
{node_xml}
{flow_xml}
  </bpmn:process>
  <bpmndi:BPMNDiagram id="Diagram_{file_id}">
    <bpmndi:BPMNPlane id="Plane_{file_id}" bpmnElement="Process_{file_id}">
{chr(10).join(shapes)}
{chr(10).join(edges)}
    </bpmndi:BPMNPlane>
  </bpmndi:BPMNDiagram>
</bpmn:definitions>
"""


def p01_auth() -> str:
    """P-01. Аутентификация через API."""
    n = [
        Node("n_start", "Начало", "user", "start", 0),
        Node("n_login", "Ввод email и пароля", "user", "user", 1),
        Node("n_req", "Передача запроса на вход", "eco", "service", 2),
        Node("n_verify", "Проверка учётных данных и выдача токена", "api", "service", 3),
        Node("n_gw", "Учётные данные верны?", "eco", "xor", 4),
        Node("n_profile", "Получение профиля пользователя", "api", "service", 5),
        Node("n_sync", "Синхронизация пользователя и роли", "eco", "service", 6),
        Node("n_session", "Сохранение токена в сессии", "eco", "service", 7),
        Node("n_redirect", "Перенаправление на домашнюю страницу", "eco", "service", 8),
        Node("n_end_ok", "Конец (вход выполнен)", "user", "end", 9),
        Node("n_err", "Отображение сообщения об ошибке", "user", "user", 5),
        Node("n_end_fail", "Конец (ошибка входа)", "user", "end_err", 6),
    ]
    f = [
        Flow("f01", "n_start", "n_login"),
        Flow("f02", "n_login", "n_req"),
        Flow("f03", "n_req", "n_verify"),
        Flow("f04", "n_verify", "n_gw"),
        Flow("f_yes", "n_gw", "n_profile", "да"),
        Flow("f_no", "n_gw", "n_err", "нет"),
        Flow("f05", "n_profile", "n_sync"),
        Flow("f06", "n_sync", "n_session"),
        Flow("f07", "n_session", "n_redirect"),
        Flow("f08", "n_redirect", "n_end_ok"),
        Flow("f_err", "n_err", "n_end_fail"),
    ]
    return build_process("P01_Auth", "P-01. Аутентификация через API", n, f)


def p08_data_control() -> str:
    """P-08. Контроль качества данных."""
    n = [
        Node("n_start", "Начало", "user", "start", 0),
        Node("n_open", "Открыть раздел «Контроль данных»", "user", "user", 1),
        Node("n_fetch", "Запрос данных с платформы", "eco", "service", 2),
        Node("n_data", "Формирование наборов организаций и партий", "api", "service", 3),
        Node("n_org_check", "Проверка полноты данных организаций", "eco", "service", 4),
        Node("n_batch_check", "Проверка согласованности по партиям", "eco", "service", 5),
        Node("n_calc", "Расчёт уровня проблемности (severity)", "eco", "service", 6),
        Node("n_gw", "Обнаружены критические проблемы?", "eco", "xor", 7),
        Node("n_show_problem", "Отображение списка проблемных организаций", "eco", "service", 8),
        Node("n_show_ok", "Отображение сводки без критических проблем", "user", "user", 8),
        Node("n_end", "Конец", "user", "end", 10),
    ]
    f = [
        Flow("f01", "n_start", "n_open"),
        Flow("f02", "n_open", "n_fetch"),
        Flow("f03", "n_fetch", "n_data"),
        Flow("f04", "n_data", "n_org_check"),
        Flow("f05", "n_org_check", "n_batch_check"),
        Flow("f06", "n_batch_check", "n_calc"),
        Flow("f07", "n_calc", "n_gw"),
        Flow("f_yes", "n_gw", "n_show_problem", "да"),
        Flow("f_no", "n_gw", "n_show_ok", "нет"),
        Flow("f08", "n_show_problem", "n_end"),
        Flow("f09", "n_show_ok", "n_end"),
    ]
    return build_process("P08_DataControl", "P-08. Контроль качества данных", n, f)


def p14_export_journal() -> str:
    """P-13 + P-14. Просмотр журнала операций и экспорт."""
    n = [
        Node("n_start", "Начало", "user", "start", 0),
        Node("n_open", "Открыть журнал операций", "user", "user", 1),
        Node("n_filter", "Применение фильтров и пагинации", "eco", "service", 2),
        Node("n_list", "Формирование списка операций", "api", "service", 3),
        Node("n_table", "Отображение таблицы журнала", "eco", "service", 4),
        Node("n_gw", "Экспортировать отчёт?", "eco", "xor", 5),
        Node("n_end_skip", "Конец (без экспорта)", "user", "end", 6),
        Node("n_format", "Выбор формата PDF / XML", "user", "user", 7),
        Node("n_build", "Формирование файла отчёта", "eco", "service", 8),
        Node("n_download", "Скачивание файла", "user", "user", 9),
        Node("n_end_ok", "Конец", "user", "end", 10),
    ]
    f = [
        Flow("f01", "n_start", "n_open"),
        Flow("f02", "n_open", "n_filter"),
        Flow("f03", "n_filter", "n_list"),
        Flow("f04", "n_list", "n_table"),
        Flow("f05", "n_table", "n_gw"),
        Flow("f_yes", "n_gw", "n_format", "да"),
        Flow("f_no", "n_gw", "n_end_skip", "нет"),
        Flow("f06", "n_format", "n_build"),
        Flow("f07", "n_build", "n_download"),
        Flow("f08", "n_download", "n_end_ok"),
    ]
    return build_process(
        "P14_ExportJournal",
        "P-14. Просмотр и экспорт журнала операций",
        n,
        f,
    )


def p17_measurement() -> str:
    """P-17. Создание экологического измерения."""
    n = [
        Node("n_start", "Начало", "user", "start", 0),
        Node("n_open", "Открыть форму нового измерения", "user", "user", 1),
        Node("n_load", "Загрузка справочников для формы", "eco", "service", 2),
        Node("n_lists", "Формирование списков организаций и партий", "api", "service", 3),
        Node("n_fill", "Ввод параметров измерения", "user", "user", 4),
        Node("n_valid", "Валидация данных формы", "eco", "service", 5),
        Node("n_gw", "Данные корректны?", "eco", "xor", 6),
        Node("n_save", "Сохранение экологического измерения", "api", "service", 7),
        Node("n_done", "Переход к журналу измерений", "eco", "service", 8),
        Node("n_end_ok", "Конец (измерение сохранено)", "user", "end", 9),
        Node("n_err", "Отображение ошибок формы", "user", "user", 7),
        Node("n_end_fail", "Конец (ошибка)", "user", "end_err", 8),
    ]
    f = [
        Flow("f01", "n_start", "n_open"),
        Flow("f02", "n_open", "n_load"),
        Flow("f03", "n_load", "n_lists"),
        Flow("f04", "n_lists", "n_fill"),
        Flow("f05", "n_fill", "n_valid"),
        Flow("f06", "n_valid", "n_gw"),
        Flow("f_yes", "n_gw", "n_save", "да"),
        Flow("f_no", "n_gw", "n_err", "нет"),
        Flow("f07", "n_save", "n_done"),
        Flow("f08", "n_done", "n_end_ok"),
        Flow("f_err", "n_err", "n_end_fail"),
    ]
    return build_process(
        "P17_Measurement",
        "P-17. Создание экологического измерения",
        n,
        f,
    )


PROCESS_FILES = [
    ("eco-bpmn-p01-auth.bpmn", p01_auth),
    ("eco-bpmn-p08-data-control.bpmn", p08_data_control),
    ("eco-bpmn-p14-export-journal.bpmn", p14_export_journal),
    ("eco-bpmn-p17-measurement.bpmn", p17_measurement),
]

# Устаревшие диаграммы по ролям (заменены процессными)
LEGACY_ROLE_FILES = [
    "eco-bpmn-admin.bpmn",
    "eco-bpmn-ecologist.bpmn",
    "eco-bpmn-manager.bpmn",
]


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for legacy in LEGACY_ROLE_FILES:
        path = OUT / legacy
        if path.exists():
            path.unlink()
            print("Removed legacy", path.name)
    for name, builder in PROCESS_FILES:
        path = OUT / name
        path.write_text(builder(), encoding="utf-8")
        print("Wrote", path)


if __name__ == "__main__":
    main()
