"""Регистрация мобильных устройств для FCM push."""

from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, UserDevice
from app.schemas import DeviceRegister, DeviceRegisterOut
from app.services.auth import get_current_user

router = APIRouter(tags=["devices"])


@router.post("/devices/register", response_model=DeviceRegisterOut, status_code=201)
def register_device(
    body: DeviceRegister,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    device_id = body.device_id.strip()
    platform = body.platform.strip().lower() or "android"
    fcm_token = body.fcm_token.strip()
    now = datetime.utcnow()

    row = (
        db.query(UserDevice)
        .filter(UserDevice.user_id == current_user.id, UserDevice.device_id == device_id)
        .first()
    )
    if row is None:
        row = UserDevice(
            user_id=current_user.id,
            device_id=device_id,
            platform=platform,
            fcm_token=fcm_token,
            updated_at=now,
        )
        db.add(row)
    else:
        row.platform = platform
        row.fcm_token = fcm_token
        row.updated_at = now

    db.commit()
    db.refresh(row)
    return DeviceRegisterOut(
        device_id=row.device_id,
        platform=row.platform,
        updated_at=row.updated_at,
    )
