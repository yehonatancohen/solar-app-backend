from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc

from app.db import get_session
from app.models import Project, Visualization, User
from app.schemas import VisualizationCreate, VisualizationOut
from app.deps import active_user_required

router = APIRouter()


async def _get_owned_project(project_id: int, user: User, session: AsyncSession) -> Project:
    proj = (
        await session.execute(select(Project).where(Project.id == project_id))
    ).scalar_one_or_none()
    if not proj or proj.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Project not found")
    return proj


@router.post("/{project_id}/visualizations", response_model=VisualizationOut)
async def create_visualization(
    project_id: int,
    payload: VisualizationCreate,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(active_user_required),
):
    await _get_owned_project(project_id, user, session)
    viz = Visualization(
        project_id=project_id,
        chart_type=payload.chart_type,
        config_json=payload.config_json,
    )
    session.add(viz)
    await session.commit()
    await session.refresh(viz)
    return viz


@router.get("/{project_id}/visualizations", response_model=list[VisualizationOut])
async def list_visualizations(
    project_id: int,
    session: AsyncSession = Depends(get_session),
    user: User = Depends(active_user_required),
):
    await _get_owned_project(project_id, user, session)
    res = await session.execute(
        select(Visualization)
        .where(Visualization.project_id == project_id)
        .order_by(desc(Visualization.created_at))
    )
    return res.scalars().all()
