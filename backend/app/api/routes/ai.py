"""AI explainability route — Groq LLM analysis of screening results."""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()


class ExplainRequest(BaseModel):
    mol_result: dict   # full result dict from screening


@router.post("/explain")
async def explain_molecule(payload: ExplainRequest):
    """Get Groq LLM explanation + improvement suggestions for a screening result."""
    from app.services.groq_service import explain_result

    explanation = explain_result(payload.mol_result)

    if explanation.error and not explanation.summary:
        raise HTTPException(status_code=503, detail=explanation.error)

    return {
        "summary": explanation.summary,
        "score_explanations": explanation.score_explanations,
        "suggestions": explanation.suggestions,
        "candidate_smiles": explanation.candidate_smiles,
        "error": explanation.error,
        "disclaimer": "AI suggestions are computational only — not clinical advice.",
    }