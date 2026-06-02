"""
Celery async tasks for MolecuLab.

Heavy jobs (docking, full screening batch) run here via Celery workers.
Start worker with: celery -A app.tasks.celery_tasks worker --loglevel=info
"""

from __future__ import annotations
import asyncio
from datetime import datetime
from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "moleculab",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    worker_prefetch_multiplier=1,   # one task at a time (GPU contention)
)


@celery_app.task(bind=True, name="tasks.run_full_screening")
def run_full_screening(self, run_id: str, smiles_list: list[str], target: str = "ACE2"):
    """
    Full screening pipeline for a batch of SMILES:
    RDKit props → Tox21 → ADMET → Vina docking → verdict.
    Updates DB run record as it progresses.
    """
    from app.services.rdkit_service import compute_properties
    from app.services.deepchem_service import predict_toxicity, predict_admet
    from app.services.vina_service import dock_molecule
    from app.services.scoring_service import compute_verdict

    results = []
    total = len(smiles_list)

    for i, smiles in enumerate(smiles_list):
        self.update_state(
            state="PROGRESS",
            meta={"current": i, "total": total, "smiles": smiles[:30]},
        )

        # 1. RDKit
        props = compute_properties(smiles)
        if not props.valid:
            results.append({
                "smiles": smiles, "error": props.error,
                "verdict": "INVALID", "color": "gray",
            })
            continue

        # 2. Toxicity
        tox = predict_toxicity(smiles)

        # 3. ADMET
        admet = predict_admet(smiles)

        # 4. Docking (async Vina call)
        dock = dock_molecule(smiles, target=target)

        # 5. Verdict
        verdict = compute_verdict(
            molecule_id=f"{run_id}_{i}",
            smiles=smiles,
            lipinski_pass=props.lipinski_pass,
            qed=props.qed,
            tox_overall=tox.overall_tox_score,
            admet_score=admet.admet_score,
            binding_affinity=dock.best_affinity,
        )

        results.append({
            "smiles": smiles,
            "mol_weight": props.mol_weight,
            "logp": props.logp,
            "hbd": props.hbd,
            "hba": props.hba,
            "tpsa": props.tpsa,
            "qed": props.qed,
            "lipinski_pass": props.lipinski_pass,
            "lipinski_violations": props.lipinski_violations,
            "tox21_scores": tox.tox21_scores,
            "tox_overall": tox.overall_tox_score,
            "admet_score": admet.admet_score,
            "binding_affinity": dock.best_affinity,
            "binding_verdict": dock.verdict,
            "overall_score": verdict.overall_score,
            "verdict": verdict.verdict,
            "color": verdict.color,
        })

    return {"run_id": run_id, "results": results, "completed_at": datetime.utcnow().isoformat()}


@celery_app.task(name="tasks.dock_single")
def dock_single(smiles: str, target: str = "ACE2") -> dict:
    """Lightweight single-molecule docking task."""
    from app.services.vina_service import dock_molecule
    result = dock_molecule(smiles, target=target)
    return {
        "smiles": smiles,
        "target": target,
        "best_affinity": result.best_affinity,
        "pose_energies": result.pose_energies,
        "verdict": result.verdict,
        "pdb_pose": result.pdb_pose,
        "error": result.error,
    }
