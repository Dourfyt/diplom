PLAN_STATUS_RU = {
    "draft": "Черновик",
    "approved": "Утверждён",
    "published": "Утверждён",
    "archived": "В архиве",
}


def plan_status_ru(code: str) -> str:
    return PLAN_STATUS_RU.get(code.lower(), code)


STAGE_STATUS_RU = {
    "pending": "Ожидает",
    "in_progress": "В работе",
    "done": "Завершён",
    "delayed": "Задержка",
}
