"""Screening API — launch and poll batch screening runs."""

import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_session
from app.models.screening_run import ScreeningRun

router = APIRouter()

COMMON_TARGETS = ["ACE2", "EGFR", "CDK2", "BRAF"]


class ScreeningRequest(BaseModel):
    smiles_list: list[str]
    target: str = "ACE2"
    run_name: str | None = None


@router.post("/run")
async def start_screening_run(
    payload: ScreeningRequest,
    session: AsyncSession = Depends(get_session),
):
    """Launch an async full screening pipeline via Celery."""
    if not payload.smiles_list:
        raise HTTPException(status_code=422, detail="smiles_list cannot be empty")
    if payload.target not in COMMON_TARGETS + ["custom"]:
        raise HTTPException(status_code=422, detail=f"Unknown target. Choose from {COMMON_TARGETS}")

    run_id = str(uuid.uuid4())

    # Kick off Celery task
    try:
        from app.tasks.celery_tasks import run_full_screening
        task = run_full_screening.delay(run_id, payload.smiles_list, payload.target)
        celery_task_id = task.id
    except Exception as e:
        # If Celery/Redis unavailable, run synchronously (dev mode)
        celery_task_id = None

    run = ScreeningRun(
        id=run_id,
        status="pending" if celery_task_id else "running",
        total_molecules=len(payload.smiles_list),
        target_protein=payload.target,
        celery_task_id=celery_task_id,
    )
    session.add(run)
    await session.commit()

    return {
        "run_id": run_id,
        "status": run.status,
        "total_molecules": run.total_molecules,
        "target": payload.target,
        "celery_task_id": celery_task_id,
        "message": "Screening job queued. Poll /api/screening/status/{run_id} for updates.",
    }


@router.get("/status/{run_id}")
async def get_run_status(
    run_id: str,
    session: AsyncSession = Depends(get_session),
):
    """Poll screening run status and results."""
    result = await session.execute(select(ScreeningRun).where(ScreeningRun.id == run_id))
    run = result.scalar_one_or_none()
    if run is None:
        raise HTTPException(status_code=404, detail="Run not found")

    # If Celery task pending, check task state
    if run.celery_task_id and run.status in ("pending", "running"):
        try:
            from app.tasks.celery_tasks import celery_app
            task = celery_app.AsyncResult(run.celery_task_id)
            if task.state == "SUCCESS":
                data = task.result
                run.status = "completed"
                run.results = data.get("results", [])
                run.passed = sum(1 for r in run.results if r.get("verdict") == "PASS")
                run.failed = run.total_molecules - run.passed
                run.completed_at = datetime.utcnow()
                await session.commit()
            elif task.state == "FAILURE":
                run.status = "failed"
                run.error = str(task.result)
                await session.commit()
        except Exception:
            pass  # Redis unavailable — return current DB state

    return {
        "run_id": run.id,
        "status": run.status,
        "total_molecules": run.total_molecules,
        "passed": run.passed,
        "failed": run.failed,
        "target": run.target_protein,
        "results": run.results if run.status == "completed" else None,
        "error": run.error,
        "created_at": run.created_at.isoformat(),
        "completed_at": run.completed_at.isoformat() if run.completed_at else None,
    }


@router.get("/targets")
async def list_targets():
    """Return available protein targets."""
    return {"targets": COMMON_TARGETS}
