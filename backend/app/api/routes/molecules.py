"""Molecules API — SMILES validation and property preview."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, field_validator

from app.services.rdkit_service import compute_properties, canonicalize

router = APIRouter()


class MoleculeInput(BaseModel):
    smiles: str
    name: str | None = None

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


@router.post("/batch-validate")
async def batch_validate(payload: BatchInput):
    """Validate and compute properties for multiple SMILES."""
    results = []
    for smiles in payload.smiles_list[:100]:  # cap at 100 for sync endpoint
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
