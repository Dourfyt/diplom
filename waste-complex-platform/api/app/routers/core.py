from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, text
from sqlalchemy.orm import Session

from app.database import engine, get_db
from app.models import Department, Organization, User, WasteType
from app.schemas import (
    DepartmentOut,
    HealthOut,
    ModuleInfo,
    OrganizationOut,
    WasteTypeImportItem,
    WasteTypeImportResult,
    WasteTypeOut,
)
from app.services.auth import get_current_user
from app.services.fkko_import import registration_allowed_for
from app.services.rbac import require_roles

router = APIRouter()


def _waste_type_out(row: WasteType) -> WasteTypeOut:
    return WasteTypeOut(
        id=row.id,
        code=row.code,
        name=row.name,
        fkko_code=row.fkko_code,
        hazard_class=row.hazard_class,
        description=row.description,
        registration_allowed=registration_allowed_for(row.hazard_class),
    )


MODULES = [
    ModuleInfo(
        id="auth",
        name="Аутентификация",
        api_prefix="/api/v1/auth",
        description="Регистрация, вход, профиль пользователя (JWT)",
    ),
    ModuleInfo(
        id="admin",
        name="Администрирование",
        api_prefix="/api/v1/admin",
        description="Пользователи и аудит действий (admin)",
    ),
    ModuleInfo(
        id="accounting",
        name="Учёт поступления и классификации",
        api_prefix="/api/v1/accounting",
        description="Регистрация партий, классификация, документы (Корчагин Д.Е.)",
    ),
    ModuleInfo(
        id="planning",
        name="Планирование переработки",
        api_prefix="/api/v1/planning",
        description="Расписание, симуляция, KPI, уведомления (Долгов Е.В.)",
    ),
    ModuleInfo(
        id="monitoring",
        name="Мониторинг этапов",
        api_prefix="/api/v1/monitoring",
        description="Статусы этапов, события, QR (Хука М.М.)",
    ),
    ModuleInfo(
        id="reporting",
        name="Отчётность и экоконтроль",
        api_prefix="/api/v1/reporting",
        description="Операции, измерения, дашборд (Журавлёва М.Е.)",
    ),
]


@router.get("/health", response_model=HealthOut)
def health(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return HealthOut(status="ok", service="waste-complex-platform", database=str(engine.url.database))


@router.get("/modules", response_model=list[ModuleInfo])
def list_modules():
    return MODULES


@router.get("/organizations", response_model=list[OrganizationOut])
def list_organizations(
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("operator", "chief", "ecologist", "admin")),
):
    return db.query(Organization).order_by(Organization.name).all()


@router.get("/waste-types", response_model=list[WasteTypeOut])
def list_waste_types(
    q: str | None = Query(default=None, description="Поиск по коду, ФККО или наименованию"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=500, ge=1, le=500),
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("operator", "chief", "ecologist", "admin")),
):
    query = db.query(WasteType)
    if q:
        needle = f"%{q.strip()}%"
        query = query.filter(
            or_(
                WasteType.code.ilike(needle),
                WasteType.fkko_code.ilike(needle),
                WasteType.name.ilike(needle),
            )
        )
    rows = (
        query.order_by(WasteType.code)
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return [_waste_type_out(row) for row in rows]


@router.post("/waste-types/import", response_model=WasteTypeImportResult)
def import_waste_types(
    payload: list[WasteTypeImportItem],
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin")),
):
    if not payload:
        raise HTTPException(status_code=400, detail="Пустой список waste_types")

    codes = [item.code.strip() for item in payload]
    existing = db.query(WasteType).filter(WasteType.code.in_(codes)).all()
    by_code = {row.code: row for row in existing}

    created = 0
    updated = 0
    for item in payload:
        code = item.code.strip()
        row = by_code.get(code)
        if row is None:
            row = WasteType(
                code=code,
                name=item.name.strip(),
                fkko_code=item.fkko_code.strip(),
                hazard_class=item.hazard_class,
                description=item.description.strip(),
            )
            db.add(row)
            created += 1
            continue

        row.name = item.name.strip()
        row.fkko_code = item.fkko_code.strip()
        row.hazard_class = item.hazard_class
        row.description = item.description.strip()
        updated += 1

    db.commit()
    return WasteTypeImportResult(total=len(payload), created=created, updated=updated)


@router.get("/departments", response_model=list[DepartmentOut])
def list_departments(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    rows = db.query(Department).order_by(Department.name).all()
    if rows:
        return rows
    return [
        DepartmentOut(id=1, code="CEH-1", name="Цех-1"),
        DepartmentOut(id=2, code="CEH-2", name="Цех-2"),
    ]
