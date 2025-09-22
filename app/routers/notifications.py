from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.db import get_session
from app.models import Notification, User
from app.schemas import NotificationCreate, NotificationOut
from app.deps import auth_required

router = APIRouter()


@router.post("", response_model=NotificationOut)
async def create_notification(
    payload: NotificationCreate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(auth_required),
):
    notification = Notification(
        user_id=user.id,
        title=payload.title,
        message=payload.message,
        delivery_channel=payload.delivery_channel,
        schedule_json=payload.schedule_json,
        status="scheduled",
    )
    session.add(notification)
    await session.commit()
    await session.refresh(notification)
    return notification


@router.get("", response_model=list[NotificationOut])
async def list_notifications(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(auth_required),
):
    res = await session.execute(
        select(Notification)
        .where(Notification.user_id == user.id)
        .order_by(desc(Notification.created_at))
    )
    return res.scalars().all()
