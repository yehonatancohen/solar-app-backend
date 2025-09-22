from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.db import get_session
from app.models import Project, Report, User
from app.schemas import ReportRequest, ReportOut
from app.deps import auth_required

router = APIRouter()


async def _get_owned_project(project_id: int, user: User, session: AsyncSession) -> Project:
    proj = (
        await session.execute(select(Project).where(Project.id == project_id))
    ).scalar_one_or_none()
    if not proj or proj.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Project not found")
    return proj


@router.post("/{project_id}/reports", response_model=ReportOut)
async def generate_report(
    project_id: int,
    payload: ReportRequest,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(auth_required),
):
    await _get_owned_project(project_id, user, session)
    report = Report(
        project_id=project_id,
        format=payload.format,
        deliver_to_json=payload.deliver_to,
        status="prepared",
    )
    session.add(report)
    await session.commit()
    await session.refresh(report)
    return report


@router.get("/{project_id}/reports", response_model=list[ReportOut])
async def list_reports(
    project_id: int,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(auth_required),
):
    await _get_owned_project(project_id, user, session)
    res = await session.execute(
        select(Report)
        .where(Report.project_id == project_id)
        .order_by(desc(Report.created_at))
    )
    return res.scalars().all()
