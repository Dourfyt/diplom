from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import accounting, admin, auth, core, deviations, devices, monitoring, planning, reporting, ws_monitoring

app = FastAPI(
    title="Программный комплекс: учёт и переработка отходов",
    description=(
        "Единый REST API для модулей: учёт (Корчагин), планирование (Долгов), "
        "мониторинг (Хука), отчётность (Журавлёва). Общая PostgreSQL."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/v1/auth")
app.include_router(admin.router, prefix="/api/v1/admin")
app.include_router(core.router, prefix="/api/v1/core")
app.include_router(accounting.router, prefix="/api/v1/accounting")
app.include_router(planning.router, prefix="/api/v1/planning")
# Совместимость с модулем planning-module (те же пути /api/v1/batches, /plans, …)
app.include_router(planning.router, prefix="/api/v1")
app.include_router(monitoring.router, prefix="/api/v1/monitoring")
app.include_router(deviations.router, prefix="/api/v1")
app.include_router(deviations.router, prefix="/api/v1/monitoring")
app.include_router(devices.router, prefix="/api/v1")
app.include_router(devices.router, prefix="/api/v1/monitoring")
app.include_router(reporting.router, prefix="/api/v1/reporting")
app.include_router(ws_monitoring.router, prefix="/api/v1/ws")
app.include_router(ws_monitoring.router, prefix="/ws")


@app.get("/api/health")
def api_health():
    return {
        "status": "ok",
        "service": "waste-complex-platform",
        "modules": ["auth", "admin", "accounting", "planning", "monitoring", "reporting", "devices", "ws"],
    }
