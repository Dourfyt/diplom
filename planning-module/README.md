# Модуль планирования перерабатывающих процессов

Веб-интерфейс (тонкий клиент) программного комплекса по учёту и переработке промышленных отходов (дипломный проект Долгова Е.В.).

Расчёты, БД и REST API — на платформе **waste-complex-platform**.

## Стек

- **Frontend:** React 18, TypeScript, Vite, nginx (Docker)
- **API:** REST `/api/v1/*` платформы (FastAPI + PostgreSQL на сервере комплекса)

## Запуск

```bash
cd planning-module
docker compose up --build
```

| Сервис | URL |
|--------|-----|
| Веб-UI | http://localhost:5173 |
| API платформы (прод) | http://178.57.217.79:8080/docs |
| API локально | http://localhost:8080/docs (если поднята платформа) |

Запросы `/api/*` из контейнера проксируются на сервер платформы (`frontend/nginx.conf`).

## Разработка без Docker

```bash
cd frontend
npm install
npm run dev
```

Прокси Vite: `vite.config.ts` → платформа `http://178.57.217.79:8080`.

Прямой вызов API (нужен CORS на сервере):

```bash
# frontend/.env
VITE_API_BASE_URL=http://178.57.217.79:8080
```

## Тестовые данные

Демо-данные (партии P1–P6, линии L1–L2, план) загружаются **seed** платформы при старте `waste-complex-platform`.

## API (основное)

- `GET /api/v1/batches` — партии с приоритетом
- `POST /api/v1/plans/build` — построить план
- `POST /api/v1/plans/{id}/replan` — перепланирование после простоя
- `POST /api/v1/simulations` — сценарии baseline / accelerated / emergency
- `GET /api/v1/dashboard/kpi` — дашборд KPI
- `GET /api/v1/notifications` — уведомления T1/T2

Полная документация: `waste-complex-platform/docs/API_документация.txt`
