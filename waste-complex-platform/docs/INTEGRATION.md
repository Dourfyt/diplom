# Интеграция дипломных модулей с платформой

## Общие сущности

| Сущность | Таблица | Учёт | Планирование | Мониторинг | Отчётность |
|----------|---------|------|--------------|------------|------------|
| Партия | `waste_batches` | создание | чтение, приоритет | этапы, QR, факт переработки* | KPI, баланс |
| Журнал движения | `waste_operations` | receipt, processing, disposal | — | processing (при done этапа) | чтение, сводки |

\* Мониторинг при завершении этапа может записать `processing` в журнал учёта.
| Вид отхода | `waste_types` | справочник | — | — | аналитика |
| Организация | `organizations` | — | — | — | отчёты |
| План | `schedule_plans` | — | CRUD | косвенно | KPI |
| Этап | `batch_stage_progress` | — | sync при approve | CRUD | — |

## Подключение модуля Долгова (planning-module)

Тонкий клиент: только `frontend/`, без собственного backend.

```bash
cd planning-module && docker compose up --build
```

Запросы `/api/*` проксируются на платформу (`frontend/nginx.conf` → `:8080`).

Локальная разработка: Vite `proxy` в `vite.config.ts` или `VITE_API_BASE_URL`.

## Подключение модуля Корчагина (десктоп учёт)

- HTTP: `POST http://localhost:8080/api/v1/accounting/batches`
- Факт переработки / вывоза: `POST http://localhost:8080/api/v1/accounting/operations`
- Баланс партии: `GET http://localhost:8080/api/v1/accounting/batches/{id}/balance`
- Или прямой SQL к `waste_complex` на порту 5434

## Подключение модуля Хука (мобильный мониторинг)

- Base URL: `http://<server>:8080/api/v1/monitoring`
- Отклонения: `POST /api/v1/deviations` (multipart: `batch_id` обязателен; `photo` необязателен; опционально `progress_id`, `comment`, `deviation_type`)
- QR: поле `qr_token` в партии → `GET /batches/qr/{token}`
- При `PATCH .../stages/{id}` со `status=done` — опциональная запись `processing` в журнал

## Подключение модуля Журавлёвой (Django отчётность)

- `GET /api/v1/reporting/dashboard`
- `GET /api/v1/core/organizations`, `/core/waste-types`
- Общая БД: те же таблицы `waste_operations`, `environmental_measurements`

## CORS

По умолчанию разрешены: `http://localhost:8080`, `5173`, `3000`.  
Добавить origin: переменная `CORS_ORIGINS` в `docker-compose.yml`.
