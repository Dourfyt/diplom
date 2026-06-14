# Учёт и переработка промышленных отходов

Монорепозиторий дипломного комплекса:

| Каталог | Описание |
|---------|----------|
| `waste-complex-platform/` | Единый API (FastAPI + PostgreSQL) |
| `planning-module/` | Модуль планирования (React) |
| `eco/` | Модуль отчётности (Django) |
| `landing/` | Лендинг комплекса + скачивание EcoDesk/APK |

## Запуск на сервере

```bash
docker compose -f docker-compose.stack.yml up -d --build
```

**Лендинг:** http://runcourse.online  
**Модули:** plan.runcourse.online · eco.runcourse.online · api.runcourse.online

Подробнее: [DEPLOY_STACK.md](DEPLOY_STACK.md)

## Справочник ФККО

Исходный файл: `ФККО.json`. Импорт в API:

```bash
POST /api/v1/core/waste-types/import
```

(роль `admin`, см. Swagger на `:8080/docs`)
