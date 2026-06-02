"""
AutoDock Vina docking service.

Wraps the `vina` Python bindings. The receptor .pdb files for common
drug targets (ACE2, EGFR, etc.) are pre-downloaded in data/proteins/.

Binding energy threshold from spec: < -7 kcal/mol = strong binder.
"""

from __future__ import annotations
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

try:
    from vina import Vina
    VINA_AVAILABLE = True
except ImportError:
    VINA_AVAILABLE = False
    logger.warning("AutoDock Vina not installed. Docking will be unavailable.")

try:
    from rdkit import Chem
    from rdkit.Chem import AllChem
    RDKIT_AVAILABLE = True
except ImportError:
    RDKIT_AVAILABLE = False

# Default search box centres for common targets (x, y, z, size_x, size_y, size_z)
TARGET_BOXES: dict[str, tuple[float, float, float, float, float, float]] = {
    "ACE2":  (  -9.2,  10.5,  54.3, 25, 25, 25),
    "EGFR":  ( -44.0,  21.3,  32.1, 20, 20, 20),
    "CDK2":  (  22.0,  -1.5,  43.7, 20, 20, 20),
    "BRAF":  ( -11.3,  15.2,  40.5, 22, 22, 22),
    "custom": (0.0, 0.0, 0.0, 25, 25, 25),  # user-supplied box
}

DATA_DIR = Path(__file__).parent.parent / "data" / "proteins"


@dataclass
class DockingResult:
    target: str
    best_affinity: float | None = None   # kcal/mol
    pose_energies: list[float] | None = None
    pdb_pose: str | None = None           # best pose as PDB string
    verdict: str | None = None            # "strong" | "moderate" | "weak"
    error: str | None = None


def smiles_to_pdbqt(smiles: str) -> str | None:
    """Convert SMILES → 3D SDF → PDBQT using RDKit + meeko (if available)."""
    if not RDKIT_AVAILABLE:
        return None
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None
    mol = Chem.AddHs(mol)
    result = AllChem.EmbedMolecule(mol, AllChem.ETKDGv3())
    if result == -1:
        return None
    AllChem.MMFFOptimizeMolecule(mol)

    try:
        from meeko import MoleculePreparation
        preparator = MoleculePreparation()
        preparator.prepare(mol)
        return preparator.write_pdbqt_string()
    except ImportError:
        # Fallback: write SDF and let vina handle it (less ideal)
        with tempfile.NamedTemporaryFile(suffix=".sdf", delete=False, mode="w") as f:
            writer = Chem.SDWriter(f.name)
            writer.write(mol)
            writer.close()
            return f.name  # caller must handle SDF path vs PDBQT string


def dock_molecule(smiles: str, target: str = "ACE2") -> DockingResult:
    """
    Run AutoDock Vina docking for a SMILES against a pre-prepared receptor.

    Returns DockingResult with binding energy (kcal/mol) and PDB pose.
    """
    result = DockingResult(target=target)

    if not VINA_AVAILABLE:
        result.error = "AutoDock Vina not installed (pip install vina)"
        return result

    receptor_path = DATA_DIR / f"{target}.pdbqt"
    if not receptor_path.exists():
        result.error = (
            f"Receptor file not found: {receptor_path}. "
            "Download from RCSB PDB and prepare with prepare_receptor4.py."
        )
        return result

    if target not in TARGET_BOXES:
        result.error = f"Unknown target '{target}'. Add box coords to TARGET_BOXES."
        return result

    cx, cy, cz, sx, sy, sz = TARGET_BOXES[target]

    ligand_pdbqt = smiles_to_pdbqt(smiles)
    if ligand_pdbqt is None:
        result.error = "Failed to generate 3D conformer from SMILES"
        return result

    try:
        v = Vina(sf_name="vina", verbosity=0)
        v.set_receptor(str(receptor_path))

        if ligand_pdbqt.endswith(".sdf"):
            v.set_ligand_from_file(ligand_pdbqt)
            os.unlink(ligand_pdbqt)
        else:
            v.set_ligand_from_string(ligand_pdbqt)

        v.compute_vina_maps(center=[cx, cy, cz], box_size=[sx, sy, sz])
        v.dock(exhaustiveness=8, n_poses=5)

        energies = v.energies(n_poses=5)
        result.pose_energies = [round(e[0], 3) for e in energies]
        result.best_affinity = result.pose_energies[0]
        result.pdb_pose = v.poses(n_poses=1, energy_range=3)

        # Verdict from spec
        if result.best_affinity <= -7.0:
            result.verdict = "strong"
        elif result.best_affinity <= -5.0:
            result.verdict = "moderate"
        else:
            result.verdict = "weak"

    except Exception as e:
        result.error = str(e)
        logger.error(f"Docking failed for {smiles[:20]}: {e}")

    return result
