"""Docking API route — AutoDock Vina via Celery."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()


class DockingRequest(BaseModel):
    smiles: str
    target: str = "ACE2"
    async_run: bool = True


@router.post("/run")
async def run_docking(payload: DockingRequest):
    """
    Dock a single molecule against a protein target.
    Set async_run=false for synchronous (blocks until done).
    """
    from app.services.rdkit_service import canonicalize

    canonical = canonicalize(payload.smiles)
    if canonical is None:
        raise HTTPException(status_code=422, detail="Invalid SMILES")

    if payload.async_run:
        try:
            from app.tasks.celery_tasks import dock_single
            task = dock_single.delay(canonical, payload.target)
            return {
                "task_id": task.id,
                "status": "queued",
                "message": f"Poll /api/docking/result/{task.id} for results.",
            }
        except Exception as e:
            pass  # Fall through to sync

    # Synchronous fallback
    from app.services.vina_service import dock_molecule
    result = dock_molecule(canonical, payload.target)
    return {
        "smiles": canonical,
        "target": payload.target,
        "best_affinity": result.best_affinity,
        "pose_energies": result.pose_energies,
        "verdict": result.verdict,
        "pdb_pose": result.pdb_pose,
        "error": result.error,
        "disclaimer": "Computational predictions for research purposes only.",
    }


@router.get("/result/{task_id}")
async def get_docking_result(task_id: str):
    """Poll Celery docking task by task ID."""
    try:
        from app.tasks.celery_tasks import celery_app
        task = celery_app.AsyncResult(task_id)
        if task.state == "PENDING":
            return {"task_id": task_id, "status": "pending"}
        if task.state == "PROGRESS":
            return {"task_id": task_id, "status": "running", "meta": task.info}
        if task.state == "SUCCESS":
            return {"task_id": task_id, "status": "completed", "result": task.result}
        if task.state == "FAILURE":
            return {"task_id": task_id, "status": "failed", "error": str(task.result)}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Celery unavailable: {e}")
