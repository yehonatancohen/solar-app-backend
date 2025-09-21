from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from app.db import get_session
from app.models import Project, ProjectInputs, Calculation, User
from app.schemas import CalcResultOut
from app.deps import auth_required
from app.calcs import solar

router = APIRouter()

@router.post("/{project_id}/calculate", response_model=CalcResultOut)
async def run_calc(project_id: int, session: AsyncSession = Depends(get_session), user: User = Depends(auth_required)):
    proj = (await session.execute(select(Project).where(Project.id == project_id))).scalar_one_or_none()
    if not proj or proj.owner_id != user.id:
        raise HTTPException(status_code=404, detail="Project not found")
    latest_inputs = (await session.execute(
        select(ProjectInputs).where(ProjectInputs.project_id == project_id).order_by(desc(ProjectInputs.version))
    )).scalars().first()
    if not latest_inputs:
        raise HTTPException(status_code=400, detail="No inputs found for project")
    # Call your algorithm module
    results = solar.calculate(latest_inputs.payload_json)
    # Version = previous calc version + 1
    last_calc = (await session.execute(select(Calculation).where(Calculation.project_id == project_id).order_by(desc(Calculation.version)))).scalars().first()
    version = (last_calc.version + 1) if last_calc else 1
    calc = Calculation(project_id=project_id, version=version, results_json=results)
    session.add(calc)
    await session.commit()
    await session.refresh(calc)
    return calc
