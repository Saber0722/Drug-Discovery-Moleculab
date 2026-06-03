"""Molecules API — SMILES validation and property preview."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, field_validator

from app.services.rdkit_service import compute_properties, canonicalize
from app.services.deepchem_service import predict_toxicity
from app.services.vina_service import dock_molecule
from app.services.scoring_service import compute_verdict

router = APIRouter()


class MoleculeInput(BaseModel):
    smiles: str
    name: str | None = None
    target: str = "ACE2"

    @field_validator("smiles")
    @classmethod
    def strip_smiles(cls, v: str) -> str:
        return v.strip()


class BatchInput(BaseModel):
    smiles_list: list[str]


@router.post("/validate")
async def validate_molecule(payload: MoleculeInput):
    """Validate SMILES and return computed RDKit properties."""
    canonical = canonicalize(payload.smiles)
    if canonical is None:
        raise HTTPException(status_code=422, detail="Invalid SMILES string")

    props = compute_properties(canonical)
    return {
        "smiles": canonical,
        "canonical_smiles": canonical,
        "name": payload.name,
        "valid": props.valid,
        "mol_weight": props.mol_weight,
        "logp": props.logp,
        "hbd": props.hbd,
        "hba": props.hba,
        "tpsa": props.tpsa,
        "rotatable_bonds": props.rotatable_bonds,
        "qed": props.qed,
        "lipinski_pass": props.lipinski_pass,
        "lipinski_violations": props.lipinski_violations,
    }


@router.post("/screen")
async def screen_molecule(payload: MoleculeInput):
    """
    Full synchronous single-molecule screening pipeline.
    RDKit → Tox21 → AutoDock Vina → weighted verdict.
    No Celery required — runs inline (docking takes 30-120s).
    """
    import uuid
    canonical = canonicalize(payload.smiles)
    if canonical is None:
        raise HTTPException(status_code=422, detail="Invalid SMILES string")

    # 1. RDKit
    props = compute_properties(canonical)
    if not props.valid:
        raise HTTPException(status_code=422, detail=props.error)

    # 2. Toxicity (DeepChem — gracefully returns None if not installed)
    tox = predict_toxicity(canonical)

    # 3. Docking (Vina — gracefully returns None affinity if not installed)
    dock = dock_molecule(canonical, target=payload.target)

    # 4. Verdict
    verdict = compute_verdict(
        molecule_id=str(uuid.uuid4()),
        smiles=canonical,
        lipinski_pass=props.lipinski_pass,
        qed=props.qed,
        tox_overall=tox.overall_tox_score,
        admet_score=None,
        binding_affinity=dock.best_affinity,
    )

    return {
        "smiles": canonical,
        "name": payload.name,
        # RDKit props
        "mol_weight": props.mol_weight,
        "logp": props.logp,
        "hbd": props.hbd,
        "hba": props.hba,
        "tpsa": props.tpsa,
        "qed": props.qed,
        "lipinski_pass": props.lipinski_pass,
        "lipinski_violations": props.lipinski_violations,
        # Toxicity
        "tox21_scores": tox.tox21_scores,
        "tox_overall": tox.overall_tox_score,
        "tox_error": tox.error,
        # Docking
        "binding_affinity": dock.best_affinity,
        "binding_verdict": dock.verdict,
        "pose_energies": dock.pose_energies,
        "docking_error": dock.error,
        # Final verdict
        "overall_score": verdict.overall_score,
        "verdict": verdict.verdict,
        "color": verdict.color,
        "disclaimer": "Computational predictions for research purposes only.",
    }


@router.post("/batch-validate")
async def batch_validate(payload: BatchInput):
    """Validate and compute RDKit properties for multiple SMILES (fast, no docking)."""
    results = []
    for smiles in payload.smiles_list[:100]:
        canonical = canonicalize(smiles)
        if canonical is None:
            results.append({"smiles": smiles, "valid": False, "error": "Invalid SMILES"})
            continue
        props = compute_properties(canonical)
        results.append({
            "smiles": canonical,
            "valid": props.valid,
            "mol_weight": props.mol_weight,
            "logp": props.logp,
            "qed": props.qed,
            "lipinski_pass": props.lipinski_pass,
        })
    return {"count": len(results), "results": results}