from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.db import get_session
from app.models import SocialLink, Dashboard, User
from app.schemas import (
    SocialLinkCreate,
    SocialLinkOut,
    DashboardCreate,
    DashboardOut,
)
from app.deps import auth_required

router = APIRouter()


@router.post("/social-links", response_model=SocialLinkOut)
async def create_social_link(
    payload: SocialLinkCreate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(auth_required),
):
    link = SocialLink(user_id=user.id, platform=payload.platform, handle=payload.handle)
    session.add(link)
    await session.commit()
    await session.refresh(link)
    return link


@router.get("/social-links", response_model=list[SocialLinkOut])
async def list_social_links(
    session: AsyncSession = Depends(get_session),
    user: User = Depends(auth_required),
):
    res = await session.execute(
        select(SocialLink)
        .where(SocialLink.user_id == user.id)
        .order_by(desc(SocialLink.created_at))
    )
    return res.scalars().all()


@router.post("/dashboards", response_model=DashboardOut)
async def create_dashboard(
    payload: DashboardCreate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(auth_required),
):
    dash = Dashboard(
        user_id=user.id,
        name=payload.name,
        preference=payload.preference,
        layout_json=payload.layout_json,
    )
    session.add(dash)
    await session.commit()
    await session.refresh(dash)
    return dash


@router.get("/dashboards", response_model=list[DashboardOut])
async def list_dashboards(
    preference: str | None = None,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(auth_required),
):
    stmt = select(Dashboard).where(Dashboard.user_id == user.id)
    if preference:
        stmt = stmt.where(Dashboard.preference == preference)
    stmt = stmt.order_by(desc(Dashboard.created_at))
    res = await session.execute(stmt)
    return res.scalars().all()
