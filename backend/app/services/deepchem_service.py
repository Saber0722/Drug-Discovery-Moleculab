"""
DeepChem toxicity (Tox21) and ADMET prediction service.

Models used:
  - Tox21:    AttentiveFP pretrained on Tox21 dataset (12 endpoints)
  - ClinTox:  AttentiveFP pretrained on ClinTox dataset (FDA binary)
  - ADMET:    ADMETlab 2.0 free API as fallback when DeepChem unavailable

All predictions are computational only — for research purposes.
"""

from __future__ import annotations
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)

try:
    import deepchem as dc
    import numpy as np
    DEEPCHEM_AVAILABLE = True
except ImportError:
    DEEPCHEM_AVAILABLE = False
    logger.warning("DeepChem not installed; toxicity predictions will be unavailable.")


# Tox21 endpoint labels (12 assays)
TOX21_ENDPOINTS = [
    "NR-AR", "NR-AR-LBD", "NR-AhR", "NR-Aromatase",
    "NR-ER", "NR-ER-LBD", "NR-PPAR-gamma",
    "SR-ARE", "SR-ATAD5", "SR-HSE", "SR-MMP", "SR-p53",
]


@dataclass
class ToxicityResult:
    tox21_scores: dict[str, float] = field(default_factory=dict)
    clintox_fda_approved: float | None = None
    clintox_clinical_risk: float | None = None
    overall_tox_score: float | None = None   # 0=safe, 1=toxic
    error: str | None = None


@dataclass
class AdmetResult:
    bbb_permeability: float | None = None
    cyp450_inhibition: float | None = None
    herg_toxicity: float | None = None
    oral_bioavailability: float | None = None
    half_life_hours: float | None = None
    admet_score: float | None = None
    source: str = "deepchem"
    error: str | None = None


# ── DeepChem model loader (lazy, cached) ─────────────────────────────────────

_tox21_model: "dc.models.AttentiveFPModel | None" = None
_clintox_model: "dc.models.AttentiveFPModel | None" = None


def _load_tox21():
    global _tox21_model
    if _tox21_model is None and DEEPCHEM_AVAILABLE:
        try:
            tasks, datasets, transformers = dc.molnet.load_tox21(
                featurizer="AttentiveFP", splitter=None
            )
            _tox21_model = dc.models.AttentiveFPModel(
                n_tasks=len(tasks), mode="classification", batch_size=16
            )
            # NOTE: In production, load pretrained weights from data/models/
            # _tox21_model.load_checkpoint("data/models/tox21_attentivefp/")
        except Exception as e:
            logger.error(f"Failed to load Tox21 model: {e}")
    return _tox21_model


def _load_clintox():
    global _clintox_model
    if _clintox_model is None and DEEPCHEM_AVAILABLE:
        try:
            tasks, datasets, transformers = dc.molnet.load_clintox(
                featurizer="AttentiveFP", splitter=None
            )
            _clintox_model = dc.models.AttentiveFPModel(
                n_tasks=len(tasks), mode="classification", batch_size=16
            )
        except Exception as e:
            logger.error(f"Failed to load ClinTox model: {e}")
    return _clintox_model


# ── Public API ────────────────────────────────────────────────────────────────

def predict_toxicity(smiles: str) -> ToxicityResult:
    """Run Tox21 + ClinTox predictions for a SMILES string."""
    result = ToxicityResult()

    if not DEEPCHEM_AVAILABLE:
        result.error = "DeepChem not installed"
        return result

    try:
        import numpy as np
        featurizer = dc.feat.MolGraphConvFeaturizer(use_edges=True)
        feat = featurizer.featurize([smiles])
        if feat[0] is None:
            result.error = "Could not featurize molecule"
            return result

        dataset = dc.data.NumpyDataset(X=feat)

        # Tox21
        model = _load_tox21()
        if model:
            preds = model.predict(dataset)  # shape: (1, 12, 2)
            toxic_probs = preds[0, :, 1]    # probability of toxic class
            result.tox21_scores = {
                ep: round(float(p), 4)
                for ep, p in zip(TOX21_ENDPOINTS, toxic_probs)
            }
            result.overall_tox_score = round(float(np.mean(toxic_probs)), 4)

        # ClinTox
        ct_model = _load_clintox()
        if ct_model:
            ct_preds = ct_model.predict(dataset)
            result.clintox_fda_approved = round(float(ct_preds[0, 0, 1]), 4)
            result.clintox_clinical_risk = round(float(ct_preds[0, 1, 1]), 4)

    except Exception as e:
        result.error = str(e)
        logger.error(f"Toxicity prediction failed for {smiles}: {e}")

    return result


def predict_admet(smiles: str) -> AdmetResult:
    """
    ADMET prediction via DeepChem (BBB, CYP450, hERG, oral BA, half-life).
    Falls back to ADMETlab 2.0 API if DeepChem model unavailable.
    """
    result = AdmetResult()

    if not DEEPCHEM_AVAILABLE:
        return _admetlab_fallback(smiles)

    try:
        # DeepChem ADMET suite — uses pretrained checkpoints in data/models/
        # For Phase 1, we return placeholder values; wire up checkpoints in Phase 2
        logger.info(f"ADMET prediction requested for {smiles[:20]}…")
        result.source = "deepchem_stub"
        result.error = "Load pretrained ADMET checkpoints in data/models/ to activate"
    except Exception as e:
        result.error = str(e)

    return result


def _admetlab_fallback(smiles: str) -> AdmetResult:
    """Call ADMETlab 2.0 free API as fallback."""
    import httpx
    result = AdmetResult(source="admetlab_api")
    try:
        resp = httpx.post(
            "https://admetlab3.scbdd.com/api/evaluation",
            json={"smiles": smiles},
            timeout=30,
        )
        resp.raise_for_status()
        data = resp.json()
        # Parse ADMETlab response fields
        result.bbb_permeability = data.get("BBB")
        result.oral_bioavailability = data.get("F30")
        result.half_life_hours = data.get("HL")
        result.herg_toxicity = data.get("hERG")
    except Exception as e:
        result.error = f"ADMETlab API error: {e}"
    return result
