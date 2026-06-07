# Handoff: модуль планирования (Долгов Е.В.)

Документ для передачи другому AI-агенту. Проект — **дипломный модуль планирования** в составе программного комплекса по учёту и переработке промышленных отходов.

---

## 1. Контекст и роль в комплексе

| Модуль | Автор | Роль |
|--------|-------|------|
| **planning-module** | Долгов Е.В. | Веб-модуль планирования смен (тонкий клиент) |
| **waste-complex-platform** (часть API) | общий комплекс | FastAPI + PostgreSQL — вся бизнес-логика планирования |
| **eco** | другой студент | Отчётность; читает KPI планирования через `/reporting/dashboard` |
| Учёт, мониторинг | другие части комплекса | Общая БД, REST API |

**Ключевая идея:** `planning-module` **не имеет своей БД**. React SPA → nginx/Vite proxy → `/api/v1/*` на платформе.

**Диплом:** `16_Долгов ЕВ_01062026.docx` в корне «Новая папка». **Не править `.docx` скриптами** — python-docx ломает оформление Word. Только инструкции пользователю или ручная правка.

---

## 2. Структура репозитория

```
Новая папка/
├── docker-compose.stack.yml      # полный стек: db + api + nginx + planning + eco
├── 16_Долгов ЕВ_01062026.docx     # диплом (не коммитится, в .gitignore)
├── planning-module/              # ТОЛЬКО frontend + docs
│   ├── frontend/                 # React + Vite
│   ├── docs/                     # ТЗ диаграмм, размещение рисунков
│   └── scripts/insert_figures_docx.py  # НЕ запускать без явной просьбы
└── waste-complex-platform/
    └── api/app/
        ├── routers/planning.py
        ├── services/planner.py, kpi.py, notifications.py, plan_lifecycle.py, monitoring_sync.py
        ├── models.py
        └── seed.py
```

---

## 3. Запуск и URL

```bash
cd "/Users/egor/Desktop/Новая папка"
docker compose -f docker-compose.stack.yml up -d --build
```

| Сервис | Порт | URL |
|--------|------|-----|
| API (через nginx) | 8080 | http://localhost:8080/docs |
| Planning UI | 5173 | http://localhost:5173 |
| Eco (отчётность) | 8001 | http://localhost:8001 |
| PostgreSQL | internal | `complex/complex`, БД `waste_complex` |

**Dev без Docker:**

```bash
cd planning-module/frontend && npm install && npm run dev
```

Прокси Vite: `/api` → `http://127.0.0.1:8080` (переменная `VITE_DEV_API_PROXY`).

**Прод-сервер:** `178.57.217.79:8080` (API), `:5173` (planning), `:8001` (eco) — прописано в stack compose.

---

## 4. planning-module (frontend)

### Стек

React 18, TypeScript, Vite 5, driver.js (онбординг), nginx в Docker.

### Навигация

**Нет React Router** — 5 вкладок через `useState` в `App.tsx`:

| Tab | Экран | Назначение |
|-----|-------|------------|
| `dashboard` | Обзор | KPI, загрузка L1/L2 |
| `schedule` | Расписание | Gantt, таблица операций, утверждение, replan |
| `batches` | Партии | Очередь с приоритетами |
| `simulation` | Симуляция | baseline / accelerated / emergency |
| `notifications` | Уведомления | T1/T2, подтверждение, «Проверить риски» |

### Ключевые файлы

| Файл | Назначение |
|------|------------|
| `frontend/src/App.tsx` | Главный экран, загрузка данных, все сценарии |
| `frontend/src/api.ts` | REST-клиент + TypeScript-типы |
| `frontend/src/lines.ts` | Цвета/метки линий L1/L2 (UI, из `GET /lines`) |
| `frontend/src/labels.ts` | RU-подписи статусов |
| `frontend/src/components/GanttChart.tsx` | Gantt из `schedule_items` |
| `frontend/src/components/BuildPlanModal.tsx` | «Новый план» (имя, горизонт 1–168 ч, выбор партий) |
| `frontend/src/components/ReplanModal.tsx` | Replan после простоя (линия, часы, причина) |
| `frontend/src/components/PlanPicker.tsx` | Выбор версии плана |
| `frontend/vite.config.ts` | proxy на `:8080` |

### API-клиент (`api.ts`)

База: `{VITE_API_BASE_URL}/api/v1` (пусто = same-origin через proxy).

| Метод | Путь | Назначение |
|-------|------|------------|
| GET | `/lines` | Линии L1/L2 |
| GET | `/batches` | Партии + приоритет + риск хранения |
| GET | `/plans?view=active\|all` | Планы |
| GET | `/dashboard/kpi?plan_id=` | KPI дашборд |
| GET | `/notifications` | Уведомления |
| POST | `/plans/build` | Построить черновик |
| POST | `/plans/{id}/approve` | Утвердить |
| POST | `/plans/{id}/replan` | Перепланирование |
| POST | `/simulations` | Симуляция |
| PATCH | `/notifications/{id}/ack` | Подтвердить уведомление |
| POST | `/notifications/check?plan_id=` | Принудительная проверка T1/T2 |

**Моков нет** — все данные с API платформы.

### UX-потоки (демо защиты)

1. **Обзор** — KPI после загрузки.
2. **Новый план** — 8 ч, обе линии на Gantt.
3. **Утвердить** → `sync_stages_from_plan` в мониторинг.
4. **Replan** — один раз L2 на 8 ч (не цепочка L1→L2).
5. **Симуляция** — «Аварийный» для таблицы сравнения KPI.
6. **Уведомления** — «Проверить риски» при пустом списке.
7. **Eco** — `manager@eco.local` / `eco2026` или seed: `chief@eco.local`/`chief123`, `ecologist@eco.local`/`ecologist123`.

Обновление данных — кнопка **«Обновить»**, не SSE.

---

## 5. waste-complex-platform (backend планирования)

### Роутер

`api/app/routers/planning.py` — смонтирован **дважды**:

- `/api/v1/planning/*`
- `/api/v1/*` (алиас для frontend)

### Сервисы

| Файл | Функции |
|------|---------|
| `planner.py` | `compute_priority`, `build_schedule`, `replan_after_downtime` |
| `kpi.py` | `plan_kpi` → OEE, загрузка линий, риск хранения, % выполнения плана |
| `notifications.py` | T1 (простой >0,5 ч), T2 (хранение <6 ч) |
| `plan_lifecycle.py` | DRAFT → APPROVED → ARCHIVED, версии |
| `monitoring_sync.py` | `sync_stages_from_plan`, `ensure_batch_stages` |

### Алгоритм планирования (`build_schedule`)

1. Партии со статусом `accepted` / `queued` (опционально фильтр `batch_ids`).
2. **Приоритет:** класс опасности + срочность хранения + экономика (`compute_priority`).
3. **Жадное расписание:** по `route_codes` (напр. `"L1,L2"`), нормы из `routing_operations`.
4. Учёт `line_free_at`, `horizon_hours`, смещений простоя.
5. Операции за горизонтом **не создаются** (не ошибка — просто не влезли).
6. Статус плана: `draft`; симуляции: `is_simulation=true`.

### Replan (`replan_after_downtime`)

- Клонирует набор партий из исходного плана.
- **`horizon_hours = min(old.horizon + downtime, 168)`** — фикс: иначе после replan на Gantt пропадает линия.
- Новый DRAFT с `parent_plan_id`, **без авто-утверждения**.

### Approve

1. `archive_other_approved()` — старые approved → archived.
2. `status=approved`, `approved_at=now`.
3. **`sync_stages_from_plan`** → `batch_stage_progress.planned_start/end`.
4. Симуляции утверждать **нельзя**.

### Симуляции

| Сценарий | Эффект |
|----------|--------|
| `baseline` | тот же горизонт, `is_simulation=true` |
| `accelerated` | горизонт × 0,85 |
| `emergency` | простой L2 (8 ч) по умолчанию |

Возвращает дельты KPI: idle, storage_risk, OEE.

---

## 6. Таблицы БД (планирование)

| Таблица | Назначение |
|---------|------------|
| `waste_batches` | Партии (общая с учётом): `route_codes`, `storage_deadline_hours`, `status` |
| `production_lines` | L1, L2 |
| `routing_operations` | DRY_SEP (L1), THERMAL (L2) |
| `schedule_plans` | Версии: `status`, `version_no`, `horizon_hours`, `is_simulation`, `parent_plan_id` |
| `schedule_items` | Операции Gantt: batch, line, start/end, priority |
| `notifications` | T1/T2, `source_module=planning` |
| `batch_stage_progress` | Плановые окна после approve (мониторинг) |
| `line_downtimes` | Модель есть, **в UI/API replan не используется** |

Подробнее: `waste-complex-platform/docs/структура_БД.txt`.

---

## 7. Seed (демо-данные)

`api/app/seed.py` при первом запуске:

- **Линии:** L1 (4 т/ч), L2 (3 т/ч).
- **Партии P1–P6** — разные сроки хранения, маршруты, классы опасности.
- **P2, P6** — кандидаты на T2 (риск хранения).
- Создаётся approved-план на 8 ч + `sync_stages_from_plan`.
- **Пользователи:** `operator@eco.local`/`operator123`, `chief@eco.local`/`chief123`, `ecologist@eco.local`/`ecologist123`, `admin@eco.local`/`admin123`.

---

## 8. Интеграция с другими модулями

```
[Учёт] waste_batches ──► [Planning] build_schedule
                              │
                    approve ──┼──► sync_stages_from_plan ──► [Мониторинг]
                              │
                              └──► plan_kpi ──► [Planning UI :5173]
                                        │
                                        └──► GET /reporting/dashboard ──► [Eco :8001]
```

- **Planning API** — **без JWT/RBAC** (только `get_db`).
- **Reporting** — RBAC: `chief`, `ecologist`, `admin`. **Operator не видит dashboard** — by design.
- **Eco login:** `manager@eco.local` / `eco2026` (Django) или seed-пользователи платформы через JWT.
- **Eco:** блокировка входа для ролей без доступа к отчётности (правки в `eco/apps/integrations/auth_api.py`, `views.py`).

---

## 9. Auth и учётные данные

| Система | Логин | Пароль |
|---------|-------|--------|
| Planning UI | — | без авторизации |
| Eco (Django) | `manager@eco.local` | `eco2026` |
| Eco / API (seed) | `chief@eco.local` | `chief123` |
| Eco / API (seed) | `ecologist@eco.local` | `ecologist123` |

---

## 10. Документация и диаграммы

| Файл | Содержание |
|------|------------|
| `planning-module/docs/ТЗ_ДИАГРАММЫ_ПРИЛОЖЕНИЯ_А-Г.md` | Полное ТЗ для приложений А–Г |
| `planning-module/docs/РАЗМЕЩЕНИЕ_РИСУНКОВ_В_ДИПЛОМЕ.md` | Куда вставлять рисунки/скрины |
| `waste-complex-platform/docs/API_документация.txt` | REST API комплекса |
| `waste-complex-platform/docs/структура_БД.txt` | Схема БД |

**Исходники диаграмм** (`planning-module/docs/diagram-appendices/`):

| Файл | Приложение / рисунок |
|------|----------------------|
| `bpmn-planning.mmd` | BPMN основной процесс |
| `bpmn-planning-replan-sim.puml` | BPMN replan + симуляция |
| `uml-components.puml` | UML компонентов (убрать/пометить SSE, Celery) |
| `activity-planning-build-plan.puml` | UML Activity построение плана |
| `er-logical-planning.puml`, `er-model.mmd` | ER-модель |
| `ui-mockups.*` | Макеты UI (приложение Г) |

---

## 11. Что в дипломе vs что в прототипе

**Есть в прототипе:**

- REST, PostgreSQL, build/approve/replan/simulate, Gantt, KPI, T1/T2, sync с мониторингом.

**Нет / «перспектива» (не писать как реализованное):**

- SSE push-обновления
- Redis / Celery
- RBAC на planning UI
- MES/SCADA интеграция
- Ручное редактирование полос Gantt
- UI для весов приоритета (`operation_code` в таблице не показывается)

**Известные UX-ограничения:**

- После replan с коротким горизонтом могла пропадать линия — исправлено в `planner.py` (расширение horizon).
- Eco «Нет данных» — часто неверная роль или нет JWT.

---

## 12. Что уже делали (история сессий)

- Динамические цвета линий из `GET /lines`.
- Модалки BuildPlan / Replan, статус партий, «Проверить риски».
- Vite proxy default `127.0.0.1:8080`.
- Fix `replan_after_downtime` horizon.
- Eco: fix login roles.
- **Ошибка:** автоправка `16_Долгов ЕВ_01062026.docx` через python-docx — сломала оформление; откат на `.bak` от 4 июня. Сломанная версия с 12 картинками: `16_Долгов ЕВ_01062026.docx.broken-20250607.docx`.

---

## 13. Правила для следующего агента

1. **Не трогать `.docx` программно** — только текстовые инструкции пользователю.
2. **Не коммитить** без явной просьбы; `.docx` в `.gitignore`.
3. Минимальный diff — не рефакторить лишнее.
4. Planning = thin client; логика — только в `waste-complex-platform/api`.
5. После правок backend: `docker compose -f docker-compose.stack.yml up -d --build api planning`.
6. Формулы в дипломе — как у Журавлёвой: центр + табуляция + номер `(N)` + блок «где» (не inline, не Equation Editor).

---

## 14. Типичные задачи

| Задача | Где править |
|--------|-------------|
| Новый endpoint / алгоритм | `waste-complex-platform/api/app/services/`, `routers/planning.py` |
| UI, Gantt, модалки | `planning-module/frontend/src/` |
| Демо-данные | `seed.py` |
| Диаграммы диплома | `planning-module/docs/diagram-appendices/*.puml` |
| Интеграция eco | `eco/apps/integrations/` |
| Полный стек | `docker-compose.stack.yml` |

---

## 15. Оформление формул в дипломе (кратко)

По образцу `16_Журавлева_МЕ_06062026.docx`:

1. Текст: «… рассчитывается по формуле (N).»
2. Пустая строка.
3. Строка по центру с табуляциями: `[Tab] Формула [Tab] (N)` — Times New Roman 14.
4. Пустая строка.
5. «где» с красной строкой 1,25 см.
6. Расшифровка символов (каждый — отдельный абзац, `;` в конце).
7. Подстановка чисел обычным абзацем.

Знаки: **−** (минус), **×** (умножение), запятая в дробях (**714,3**). Редактор формул Word не нужен.

---

*Обновлено: июнь 2026. Автор модуля: Долгов Е.В., специальность 09.02.07.*
