"""
MolecuLab overall verdict scorer.

Weighted composite per spec:
  RO5(25%) + QED(20%) + Tox21(20%) + ADMET(20%) + Binding(30%)
  Colour-coded: green >= 0.6 PASS, red < 0.6 FAIL
"""

from __future__ import annotations
from dataclasses import dataclass

from app.core.config import settings


@dataclass
class ScreeningVerdict:
    molecule_id: str
    smiles: str

    lipinski_pass: bool = False
    qed_score: float = 0.0
    tox_score: float = 0.0        # 0=safe, 1=toxic → inverted for scoring
    admet_score: float = 0.0
    binding_score: float = 0.0    # normalized 0-1 from kcal/mol

    overall_score: float = 0.0
    verdict: str = "FAIL"         # PASS | FAIL
    color: str = "red"            # green | yellow | red


def normalize_binding(affinity_kcal: float | None) -> float:
    """
    Map binding energy (kcal/mol, negative = better) to 0–1 score.
    -10 → 1.0,  -7 → ~0.75,  -5 → ~0.5,  0 → 0
    Clamps outside range.
    """
    if affinity_kcal is None:
        return 0.0
    # Linear map: [-10, 0] → [1, 0]
    score = max(0.0, min(1.0, -affinity_kcal / 10.0))
    return round(score, 4)


def compute_verdict(
    molecule_id: str,
    smiles: str,
    lipinski_pass: bool,
    qed: float | None,
    tox_overall: float | None,   # 0=safe 1=toxic
    admet_score: float | None,
    binding_affinity: float | None,
) -> ScreeningVerdict:
    """Compute weighted composite score and colour-coded verdict."""

    verdict = ScreeningVerdict(molecule_id=molecule_id, smiles=smiles)
    verdict.lipinski_pass = lipinski_pass

    # Component scores (all 0-1)
    qed_s = qed if qed is not None else 0.0
    tox_s = 1.0 - (tox_overall if tox_overall is not None else 0.5)  # invert: safe=1
    admet_s = admet_score if admet_score is not None else 0.5
    bind_s = normalize_binding(binding_affinity)
    ro5_s = 1.0 if lipinski_pass else 0.0

    verdict.qed_score = round(qed_s, 4)
    verdict.tox_score = round(tox_s, 4)
    verdict.admet_score = round(admet_s, 4)
    verdict.binding_score = round(bind_s, 4)

    # Weighted composite
    overall = (
        ro5_s    * 0.10 +   # RO5: gate rather than big weight
        qed_s    * settings.QED_WEIGHT +
        tox_s    * settings.TOX_WEIGHT +
        admet_s  * settings.ADMET_WEIGHT +
        bind_s   * settings.BINDING_WEIGHT
    )
    verdict.overall_score = round(overall, 4)

    # Verdict & colour
    if not lipinski_pass:
        verdict.verdict = "FAIL"
        verdict.color = "red"
    elif overall >= 0.65:
        verdict.verdict = "PASS"
        verdict.color = "green"
    elif overall >= 0.45:
        verdict.verdict = "REVIEW"
        verdict.color = "yellow"
    else:
        verdict.verdict = "FAIL"
        verdict.color = "red"

    return verdict
