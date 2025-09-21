from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.db import get_session
from app.models import Project, ProjectInputs, Calculation, User
from app.schemas import ProjectCreate, ProjectOut, InputsCreate, InputsOut
from app.deps import auth_required

router = APIRouter()

@router.post("", response_model=ProjectOut)
async def create_project(payload: ProjectCreate, session: AsyncSession = Depends(get_session), user: User = Depends(auth_required)):
    proj = Project(owner_id=user.id, org_id=user.org_id, name=payload.name, site_location_json=payload.site_location_json, currency=payload.currency)
    session.add(proj)
    await session.commit()
    await session.refresh(proj)
    return proj

@router.get("", response_model=list[ProjectOut])
async def list_projects(session: AsyncSession = Depends(get_session), user: User = Depends(auth_required)):
    res = await session.execute(select(Project).where(Project.owner_id == user.id).order_by(desc(Project.created_at)))
    return res.scalars().all()

@router.post("/{project_id}/inputs", response_model=InputsOut)
async def save_inputs(project_id: int, payload: InputsCreate, session: AsyncSession = Depends(get_session), user: User = Depends(auth_required)):
    proj = (await session.execute(select(Project).where(Project.id == project_id))).scalar_one_or_none()
    if not proj or proj.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Project not found")
    # Versioning: increment last version
    last = (await session.execute(select(ProjectInputs).where(ProjectInputs.project_id == project_id).order_by(desc(ProjectInputs.version)))).scalars().first()
    version = (last.version + 1) if last else 1
    rec = ProjectInputs(project_id=project_id, version=version, payload_json=payload.payload_json)
    session.add(rec)
    await session.commit()
    await session.refresh(rec)
    return rec
