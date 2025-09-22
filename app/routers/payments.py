from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db import get_session
from app.models import PaymentMethod, User
from app.schemas import PaymentMethodOut
from app.deps import auth_required

router = APIRouter()


@router.get("/me", response_model=PaymentMethodOut)
async def get_my_payment_method(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(auth_required),
):
    res = await session.execute(
        select(PaymentMethod).where(PaymentMethod.user_id == user.id)
    )
    method = res.scalars().first()
    if not method:
        raise HTTPException(status_code=404, detail="Payment method not found")
    return method

