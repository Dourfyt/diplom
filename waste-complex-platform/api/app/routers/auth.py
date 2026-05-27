from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.schemas import TokenOut, UserLogin, UserOut, UserPasswordChange, UserRegister
from app.services.audit import log_action
from app.services.auth import create_access_token, get_current_user, hash_password, verify_password
from app.services.rbac import require_roles

router = APIRouter(tags=["auth"])


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register(body: UserRegister, db: Session = Depends(get_db)):
    # bootstrap: первый пользователь может быть создан без admin
    users_count = db.query(User).count()
    if users_count > 0:
        raise HTTPException(
            status_code=403,
            detail="Публичная регистрация отключена. Используйте /api/v1/admin/users",
        )
    email = body.email.strip().lower()
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=400, detail="Пользователь с таким email уже существует")

    user = User(
        email=email,
        password_hash=hash_password(body.password),
        full_name=body.full_name.strip(),
        role=body.role,
    )
    db.add(user)
    log_action(db, user=user, action="user_create", entity_type="user", entity_id=None, details="bootstrap")
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=TokenOut)
def login(body: UserLogin, db: Session = Depends(get_db)):
    email = body.email.strip().lower()
    user = db.query(User).filter(User.email == email).first()
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Неверный email или пароль")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Учётная запись деактивирована")
    log_action(db, user=user, action="login", entity_type="auth", details="Успешный вход")
    db.commit()
    return TokenOut(access_token=create_access_token(user.id))


@router.get("/user", response_model=UserOut)
def get_user(current_user: User = Depends(get_current_user)):
    return current_user


@router.patch("/user/password")
def change_password(
    body: UserPasswordChange,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not verify_password(body.current_password, current_user.password_hash):
        raise HTTPException(status_code=400, detail="Текущий пароль указан неверно")
    if body.current_password == body.new_password:
        raise HTTPException(status_code=400, detail="Новый пароль должен отличаться от текущего")

    current_user.password_hash = hash_password(body.new_password)
    log_action(
        db,
        user=current_user,
        action="password_change",
        entity_type="user",
        entity_id=current_user.id,
        details="Смена пароля пользователем",
    )
    db.commit()
    return {"ok": True}


@router.post("/register-admin", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register_admin_only(
    body: UserRegister,
    _: User = Depends(require_roles("admin")),
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
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
