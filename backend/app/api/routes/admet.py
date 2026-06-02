"""ADMET API route — toxicity and pharmacokinetics."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()


class AdmetRequest(BaseModel):
    smiles: str


@router.post("/predict")
async def predict_admet(payload: AdmetRequest):
    """Predict ADMET properties for a single molecule."""
    from app.services.deepchem_service import predict_toxicity, predict_admet
    from app.services.rdkit_service import canonicalize

    canonical = canonicalize(payload.smiles)
    if canonical is None:
        raise HTTPException(status_code=422, detail="Invalid SMILES")

    tox = predict_toxicity(canonical)
    admet = predict_admet(canonical)

    return {
        "smiles": canonical,
        "toxicity": {
            "tox21_scores": tox.tox21_scores,
            "clintox_fda_approved": tox.clintox_fda_approved,
            "clintox_clinical_risk": tox.clintox_clinical_risk,
            "overall_tox_score": tox.overall_tox_score,
            "error": tox.error,
        },
        "admet": {
            "bbb_permeability": admet.bbb_permeability,
            "cyp450_inhibition": admet.cyp450_inhibition,
            "herg_toxicity": admet.herg_toxicity,
            "oral_bioavailability": admet.oral_bioavailability,
            "half_life_hours": admet.half_life_hours,
            "source": admet.source,
            "error": admet.error,
        },
        "disclaimer": (
            "Computational predictions for research purposes only — not clinical advice."
        ),
    }
