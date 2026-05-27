# Платформа API программного комплекса (дипломы)

Единая **PostgreSQL** и **REST API** для четырёх модулей одного комплекса по учёту и переработке промышленных отходов:

| Модуль | Автор (пример) | Префикс API |
|--------|----------------|-------------|
| Учёт поступления и классификации | Корчагин Д.Е. | `/api/v1/accounting` |
| Планирование переработки | Долгов Е.В. | `/api/v1/planning` |
| Мониторинг этапов | Хука М.М. | `/api/v1/monitoring` |
| Отчётность и экоконтроль | Журавлёва М.Е. | `/api/v1/reporting` |

**Nginx** на порту **8080** проксирует все запросы к API.

## Быстрый старт

```bash
cd waste-complex-platform
docker compose up --build
```

| Сервис | URL |
|--------|-----|
| API (через nginx) | http://localhost:8080/api/ |
| Swagger | http://localhost:8080/docs |
| Список модулей | http://localhost:8080/api/v1/core/modules |
| PostgreSQL | `localhost:5434`, БД `waste_complex`, user/pass `complex` |

## Совместимость с модулем планирования (Долгов)

Модуль `planning-module` — **тонкий клиент** (только frontend), подключается к API платформы:

1. **Через nginx (рекомендуется)** — во frontend `vite` proxy или nginx модуля направлять `/api` → `http://localhost:8080/api`.

2. **Прямо к API** — те же пути, что и раньше:
   - `GET /api/v1/batches`
   - `GET /api/v1/plans`
   - `POST /api/v1/plans/build`
   - …

   Дублируются и с префиксом модуля: `/api/v1/planning/batches`.

3. **Общая БД** (десктоп учёта, мобильный мониторинг):

```env
DATABASE_URL=postgresql://complex:complex@localhost:5434/waste_complex
```

## Потоки данных (таблица 9 диплома)

```
Модуль учёта  ──POST /accounting/batches──►  waste_batches
       │                                          │
       ▼                                          ▼
Модуль планирования ◄──чтение партий──  build/approve plan
       │                                          │
       ▼                                          ▼
Модуль мониторинга ◄──этапы batch_stage_progress──┘
       │
       ▼
Модуль отчётности ◄──operations, measurements, KPI
```

При **утверждении плана** (`POST .../plans/{id}/approve`) плановые окна операций записываются в этапы мониторинга.

## Основные эндпоинты

### Учёт (`/api/v1/accounting`)
- `POST /batches` — регистрация партии (+ акт приёма, журнал операции)
- `PATCH /batches/{id}/classify` — классификация
- `POST /operations` — факт переработки (`processing`) или вывоза (`disposal`/`export`)
- `GET /batches/{id}/balance` — поступило / переработано / вывезено / остаток

### Планирование (`/api/v1/planning` или `/api/v1`)
- `GET /batches`, `GET /plans`, `POST /plans/build`, `POST /plans/{id}/approve`
- `POST /simulations`, `GET /dashboard/kpi`, `GET /notifications`

### Мониторинг (`/api/v1/monitoring`)
- `GET /batches` — партии со статусами этапов
- `GET /batches/qr/{token}` — по QR-коду партии
- `PATCH /batches/{id}/stages/{stage_id}` — смена статуса этапа
- `POST /batches/{id}/stages/{stage_id}/events` — событие

### Отчётность (`/api/v1/reporting`)
- `GET /dashboard` — сводный дашборд (в т.ч. total_processed_tons, total_disposed_tons)
- `GET /summary/balances` — балансы всех партий
- `GET /operations`, `GET /measurements`
- `POST /measurements` — экологическое измерение

Подробнее: [docs/INTEGRATION.md](docs/INTEGRATION.md)

Полная документация API (txt): [docs/API_документация.txt](docs/API_документация.txt)
