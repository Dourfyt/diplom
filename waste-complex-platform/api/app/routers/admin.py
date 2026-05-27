from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import AuditLog, User
from app.schemas import AuditLogOut, UserAdminCreate, UserAdminUpdate, UserOut
from app.services.audit import log_action
from app.services.auth import hash_password
from app.services.rbac import require_roles

router = APIRouter(tags=["admin"])


@router.get("/users", response_model=list[UserOut])
def list_users(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    _: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    offset = (page - 1) * page_size
    return db.query(User).order_by(User.id).offset(offset).limit(page_size).all()


@router.post("/users", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def create_user(
    body: UserAdminCreate,
    actor: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    email = body.email.strip().lower()
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=400, detail="Пользователь с таким email уже существует")
    user = User(
        email=email,
        password_hash=hash_password(body.password),
        full_name=body.full_name.strip(),
        role=body.role,
        is_active=True,
    )
    db.add(user)
    db.flush()
    log_action(
        db,
        user=actor,
        action="user_create",
        entity_type="user",
        entity_id=user.id,
        details=f"Создан пользователь {user.email} с ролью {user.role}",
    )
    db.commit()
    db.refresh(user)
    return user


@router.patch("/users/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    body: UserAdminUpdate,
    actor: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    if body.full_name is not None:
        user.full_name = body.full_name.strip()
    if body.role is not None:
        user.role = body.role
    if body.is_active is not None:
        user.is_active = body.is_active
    log_action(
        db,
        user=actor,
        action="user_update",
        entity_type="user",
        entity_id=user.id,
        details=f"full_name={body.full_name}, role={body.role}, is_active={body.is_active}",
    )
    db.commit()
    db.refresh(user)
    return user


@router.delete("/users/{user_id}")
def deactivate_user(
    user_id: int,
    actor: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    user.is_active = False
    log_action(
        db,
        user=actor,
        action="user_deactivate",
        entity_type="user",
        entity_id=user.id,
        details=f"Деактивирован пользователь {user.email}",
    )
    db.commit()
    return {"ok": True}


@router.get("/audit-logs", response_model=list[AuditLogOut])
def get_audit_logs(
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
    user_id: int | None = Query(default=None),
    action: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=100, ge=1, le=500),
    _: User = Depends(require_roles("admin")),
    db: Session = Depends(get_db),
):
    from datetime import datetime

    q = db.query(AuditLog).order_by(AuditLog.created_at.desc())
    if date_from:
        q = q.filter(AuditLog.created_at >= datetime.fromisoformat(date_from))
    if date_to:
        q = q.filter(AuditLog.created_at <= datetime.fromisoformat(date_to))
    if user_id is not None:
        q = q.filter(AuditLog.user_id == user_id)
    if action:
        q = q.filter(AuditLog.action == action)
    rows = q.offset((page - 1) * page_size).limit(page_size).all()
    result: list[AuditLogOut] = []
    for row in rows:
        result.append(
            AuditLogOut(
                id=row.id,
                user_id=row.user_id,
                user_name=row.user.full_name if row.user else None,
                action=row.action,
                entity_type=row.entity_type,
                entity_id=row.entity_id,
                details=row.details,
                created_at=row.created_at,
            )
        )
    return result
