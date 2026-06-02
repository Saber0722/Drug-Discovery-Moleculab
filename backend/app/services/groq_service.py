"""
Groq AI explainability service.

Given a molecule's screening result, calls Groq LLM to:
1. Explain in plain English why each score is low
2. Suggest scaffold hops / bioisostere swaps
3. Propose up to 3 improved SMILES candidates

Uses llama-3.3-70b-versatile via Groq's OpenAI-compatible API.
"""

from __future__ import annotations
import json
import httpx
from dataclasses import dataclass, field

from app.core.config import settings


@dataclass
class AIExplanation:
    summary: str = ""
    score_explanations: dict[str, str] = field(default_factory=dict)
    suggestions: list[str] = field(default_factory=list)   # plain-text suggestions
    candidate_smiles: list[str] = field(default_factory=list)  # up to 3
    error: str | None = None


def explain_result(mol_result: dict) -> AIExplanation:
    """
    Takes a screening result dict and returns an AI explanation.
    mol_result keys: smiles, qed, logp, mol_weight, lipinski_pass,
                     lipinski_violations, tox_overall, admet_score,
                     binding_affinity, overall_score, verdict
    """
    if not settings.GROQ_API_KEY:
        result = AIExplanation()
        result.error = "GROQ_API_KEY not set in .env"
        return result

    prompt = _build_prompt(mol_result)

    try:
        resp = httpx.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.GROQ_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": "llama-3.3-70b-versatile",
                "temperature": 0.3,
                "max_tokens": 800,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "You are a medicinal chemist AI assistant. "
                            "Analyse drug screening results and suggest improvements. "
                            "Always respond with valid JSON only — no markdown, no preamble."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
            },
            timeout=30,
        )
        resp.raise_for_status()
        raw = resp.json()["choices"][0]["message"]["content"].strip()

        # Strip accidental markdown fences
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        data = json.loads(raw)

        return AIExplanation(
            summary=data.get("summary", ""),
            score_explanations=data.get("score_explanations", {}),
            suggestions=data.get("suggestions", []),
            candidate_smiles=data.get("candidate_smiles", []),
        )

    except Exception as e:
        result = AIExplanation()
        result.error = str(e)
        return result


def _build_prompt(r: dict) -> str:
    violations = ", ".join(r.get("lipinski_violations") or []) or "none"
    return f"""
Analyse this drug screening result and respond with JSON only.

Molecule SMILES: {r.get("smiles", "?")}
Overall verdict: {r.get("verdict", "?")} (score: {r.get("overall_score", "?")})

Scores:
- Molecular weight: {r.get("mol_weight", "?")} Da
- LogP: {r.get("logp", "?")}
- HBD/HBA: {r.get("hbd", "?")}/{r.get("hba", "?")}
- QED (drug-likeness 0-1): {r.get("qed", "?")}
- Lipinski RO5: {"PASS" if r.get("lipinski_pass") else "FAIL"} — violations: {violations}
- Tox21 overall (0=safe, 1=toxic): {r.get("tox_overall", "not available")}
- ADMET score: {r.get("admet_score", "not available")}
- Binding affinity: {r.get("binding_affinity", "not available")} kcal/mol

Respond with this exact JSON structure:
{{
  "summary": "2-3 sentence plain-English summary of why this molecule passed or failed",
  "score_explanations": {{
    "qed": "one sentence about the QED score",
    "lipinski": "one sentence about RO5 compliance",
    "toxicity": "one sentence about tox21 result",
    "binding": "one sentence about binding affinity"
  }},
  "suggestions": [
    "Specific structural modification suggestion 1",
    "Specific structural modification suggestion 2",
    "Specific structural modification suggestion 3"
  ],
  "candidate_smiles": [
    "modified_smiles_1_if_possible",
    "modified_smiles_2_if_possible"
  ]
}}

For candidate_smiles: only include if you can make a confident, valid SMILES modification.
Keep suggestions concrete and chemically meaningful.
"""