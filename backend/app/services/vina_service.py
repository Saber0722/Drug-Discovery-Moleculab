"""
AutoDock Vina docking service.

Box coordinates computed from actual binding site residues:
- ACE2  (1R42): zinc peptidase active site (His374, His378, Glu402, His540)
- EGFR  (1M17): ATP binding pocket (Thr766, Met769, Lys745, Thr790)
- CDK2  (1HCL): ATP/inhibitor binding site (Leu83, His84, Gln85, Asp145)
- BRAF  (1UWH): kinase domain DFG pocket (Cys532, Asp594, Phe595)
"""

from __future__ import annotations
import os
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

try:
    from vina import Vina
    VINA_AVAILABLE = True
except ImportError:
    VINA_AVAILABLE = False
    logger.warning("AutoDock Vina not installed — run: uv add vina meeko")

try:
    from rdkit import Chem
    from rdkit.Chem import AllChem
    RDKIT_AVAILABLE = True
except ImportError:
    RDKIT_AVAILABLE = False

# Box centres + sizes (Å) — derived from actual binding site residue coordinates
TARGET_BOXES: dict[str, dict] = {
    "ACE2": dict(center=[46.2, 71.7, 34.2], size=[25, 25, 25]),
    "EGFR": dict(center=[24.8,  8.6, 60.5], size=[22, 22, 22]),
    "CDK2": dict(center=[104.2, 100.4, 78.0], size=[22, 22, 22]),
    "BRAF": dict(center=[83.8, 35.3, 66.8], size=[22, 22, 22]),
}

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "proteins"


@dataclass
class DockingResult:
    target: str
    best_affinity: float | None = None
    pose_energies: list[float] = field(default_factory=list)
    pdb_pose: str | None = None
    verdict: str | None = None   # strong | moderate | weak
    error: str | None = None


def _smiles_to_pdbqt_string(smiles: str) -> str | None:
    """SMILES → 3D conformer → PDBQT string via meeko."""
    if not RDKIT_AVAILABLE:
        return None
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None
    mol = Chem.AddHs(mol)
    if AllChem.EmbedMolecule(mol, AllChem.ETKDGv3()) == -1:
        return None
    AllChem.MMFFOptimizeMolecule(mol)

    try:
        from meeko import MoleculePreparation, PDBQTWriterLegacy
        preparator = MoleculePreparation()
        mol_setups = preparator.prepare(mol)
        pdbqt_string, is_ok, error_msg = PDBQTWriterLegacy.write_string(mol_setups[0])
        if not is_ok:
            logger.error(f"meeko write failed: {error_msg}")
            return None
        return pdbqt_string
    except Exception as e:
        logger.warning(f"meeko failed ({e}), trying obabel fallback")
        # obabel fallback
        with tempfile.NamedTemporaryFile(suffix=".sdf", delete=False, mode="w") as f:
            sdf_path = f.name
        writer = Chem.SDWriter(sdf_path)
        writer.write(mol)
        writer.close()
        pdbqt_path = sdf_path.replace(".sdf", ".pdbqt")
        try:
            subprocess.run(
                ["obabel", sdf_path, "-O", pdbqt_path, "--partialcharge", "gasteiger"],
                capture_output=True, check=True
            )
            return Path(pdbqt_path).read_text()
        except Exception as e2:
            logger.error(f"obabel fallback failed: {e2}")
            return None
        finally:
            os.unlink(sdf_path)
            if os.path.exists(pdbqt_path):
                os.unlink(pdbqt_path)


def dock_molecule(smiles: str, target: str = "ACE2") -> DockingResult:
    """Run AutoDock Vina docking. Returns DockingResult (error field set if unavailable)."""
    result = DockingResult(target=target)

    if not VINA_AVAILABLE:
        result.error = "AutoDock Vina not installed — run: uv add vina meeko"
        return result

    receptor_path = DATA_DIR / f"{target}.pdbqt"
    if not receptor_path.exists():
        result.error = f"Receptor not found: {receptor_path}"
        return result

    if target not in TARGET_BOXES:
        result.error = f"No box config for target '{target}'"
        return result

    ligand_pdbqt = _smiles_to_pdbqt_string(smiles)
    if not ligand_pdbqt:
        result.error = "Failed to generate ligand PDBQT (check meeko/obabel install)"
        return result

    try:
        v = Vina(sf_name="vina", verbosity=0)
        v.set_receptor(str(receptor_path))
        v.set_ligand_from_string(ligand_pdbqt)

        box = TARGET_BOXES[target]
        v.compute_vina_maps(center=box["center"], box_size=box["size"])
        v.dock(exhaustiveness=8, n_poses=5)

        energies = v.energies(n_poses=5)
        result.pose_energies = [round(float(e[0]), 3) for e in energies]
        result.best_affinity = result.pose_energies[0]
        result.pdb_pose = v.poses(n_poses=1, energy_range=3)

        if result.best_affinity <= -7.0:
            result.verdict = "strong"
        elif result.best_affinity <= -5.0:
            result.verdict = "moderate"
        else:
            result.verdict = "weak"

    except Exception as e:
        result.error = str(e)
        logger.error(f"Docking failed for {smiles[:30]}: {e}")

    return result