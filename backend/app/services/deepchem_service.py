"""
DeepChem toxicity (Tox21) prediction service.

Phase 1: Uses RDKit structural-alert heuristic — always returns a value.
Phase 2: Drop a trained MultitaskClassifier checkpoint into
         data/models/tox21_attentivefp/ and it will be picked up automatically.

To train the checkpoint (Phase 2), run:
    python backend/app/scripts/train_tox21.py
"""

from __future__ import annotations
from dataclasses import dataclass, field
import logging
import os

logger = logging.getLogger(__name__)

try:
    import deepchem as dc
    import numpy as np
    DEEPCHEM_AVAILABLE = True
except ImportError:
    DEEPCHEM_AVAILABLE = False
    logger.warning("DeepChem not installed; using RDKit heuristic for toxicity.")

TOX21_ENDPOINTS = [
    "NR-AR", "NR-AR-LBD", "NR-AhR", "NR-Aromatase",
    "NR-ER", "NR-ER-LBD", "NR-PPAR-gamma",
    "SR-ARE", "SR-ATAD5", "SR-HSE", "SR-MMP", "SR-p53",
]

CHECKPOINT_DIR = os.path.join(
    os.path.dirname(__file__), "..", "data", "models", "tox21_attentivefp"
)


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


# ── RDKit heuristic (Phase 1 default) ────────────────────────────────────────

def _rdkit_tox_heuristic(smiles: str) -> ToxicityResult:
    """
    Structural-alert heuristic using RDKit descriptors.
    Clearly labelled in result.error. Guarantees overall_tox_score is never None.
    """
    result = ToxicityResult()
    try:
        from rdkit import Chem
        from rdkit.Chem import Descriptors, rdMolDescriptors
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            result.overall_tox_score = 0.5
            result.error = "Invalid SMILES"
            return result

        mw    = Descriptors.MolWt(mol)
        logp  = Descriptors.MolLogP(mol)
        hbd   = rdMolDescriptors.CalcNumHBD(mol)
        rings = rdMolDescriptors.CalcNumRings(mol)
        arom  = rdMolDescriptors.CalcNumAromaticRings(mol)

        score = min(1.0, max(0.0,
            0.30 * min(logp  / 6.0, 1.0) +
            0.20 * min(mw    / 600.0, 1.0) +
            0.20 * min(arom  / 4.0, 1.0) +
            0.15 * min(rings / 5.0, 1.0) +
            0.15 * min(hbd   / 5.0, 1.0)
        ))
        result.tox21_scores = {ep: round(score, 4) for ep in TOX21_ENDPOINTS}
        result.overall_tox_score = round(score, 4)
        result.error = "heuristic: structural alert estimate — train model for real predictions"
    except Exception as e:
        result.overall_tox_score = 0.5
        result.error = f"Heuristic failed: {e}"
    return result


# ── DeepChem model loader (Phase 2, lazy + cached) ───────────────────────────

_tox21_model = None
_tox21_tasks = None


def _checkpoint_exists() -> bool:
    """True only if a real checkpoint is present (has .index file)."""
    if not os.path.isdir(CHECKPOINT_DIR):
        return False
    return any(f.endswith(".index") for f in os.listdir(CHECKPOINT_DIR))


def _load_tox21():
    global _tox21_model, _tox21_tasks
    if _tox21_model is not None:
        return _tox21_model, _tox21_tasks
    if not DEEPCHEM_AVAILABLE or not _checkpoint_exists():
        return None, None
    try:
        tasks, datasets, _ = dc.molnet.load_tox21(featurizer="ECFP", splitter=None)
        _tox21_tasks = tasks
        model = dc.models.MultitaskClassifier(
            n_tasks=len(tasks),
            n_features=1024,
            layer_sizes=[512, 256],
            dropouts=0.25,
            batch_size=16,
            model_dir=CHECKPOINT_DIR,
        )
        model.restore()
        logger.info("Loaded Tox21 checkpoint from %s", CHECKPOINT_DIR)
        _tox21_model = model
        return _tox21_model, _tox21_tasks
    except Exception as e:
        logger.error("Failed to load Tox21 checkpoint: %s", e)
        return None, None


# ── Public API ────────────────────────────────────────────────────────────────

def predict_toxicity(smiles: str) -> ToxicityResult:
    """
    Tox21 prediction. Uses trained DeepChem model if checkpoint exists,
    otherwise RDKit heuristic. Always returns a non-None overall_tox_score.
    """
    model, tasks = _load_tox21()
    if model is None:
        return _rdkit_tox_heuristic(smiles)

    result = ToxicityResult()
    try:
        featurizer = dc.feat.CircularFingerprint(size=1024)
        feat = featurizer.featurize([smiles])
        dataset = dc.data.NumpyDataset(X=feat)
        preds = model.predict(dataset)          # (1, n_tasks, 2) or (1, n_tasks)

        toxic_probs = preds[0, :, 1] if preds.ndim == 3 else preds[0, :]
        result.tox21_scores = {
            ep: round(float(p), 4)
            for ep, p in zip(TOX21_ENDPOINTS, toxic_probs)
        }
        result.overall_tox_score = round(float(np.mean(toxic_probs)), 4)
    except Exception as e:
        logger.error("DeepChem prediction failed for %s: %s", smiles[:30], e)
        fallback = _rdkit_tox_heuristic(smiles)
        result.overall_tox_score = fallback.overall_tox_score
        result.tox21_scores      = fallback.tox21_scores
        result.error             = str(e)
    return result


def predict_admet(smiles: str) -> AdmetResult:
    """ADMET via ADMETlab 2.0 free API."""
    return _admetlab_fallback(smiles)


def _admetlab_fallback(smiles: str) -> AdmetResult:
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
        result.bbb_permeability     = data.get("BBB")
        result.oral_bioavailability = data.get("F30")
        result.half_life_hours      = data.get("HL")
        result.herg_toxicity        = data.get("hERG")
    except Exception as e:
        result.error = f"ADMETlab API error: {e}"
    return result