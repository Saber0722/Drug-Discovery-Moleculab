"""
RDKit property computation service.

Computes all Lipinski RO5 descriptors, QED, TPSA, and the
overall weighted verdict defined in the MolecuLab scoring spec:

  overall = RO5(pass/fail) + QED(20%) + Tox21(20%) + ADMET(20%) + Binding(30%)

This module handles the purely local, CPU-bound RDKit layer.
DeepChem toxicity and ADMET are in their own services.
"""

from __future__ import annotations
from dataclasses import dataclass, field

try:
    from rdkit import Chem
    from rdkit.Chem import Descriptors, QED, rdMolDescriptors
    RDKIT_AVAILABLE = True
except ImportError:
    RDKIT_AVAILABLE = False

from app.core.config import settings


@dataclass
class MoleculeProperties:
    smiles: str
    valid: bool = False
    error: str | None = None

    # Lipinski
    mol_weight: float | None = None
    logp: float | None = None
    hbd: int | None = None
    hba: int | None = None
    tpsa: float | None = None
    rotatable_bonds: int | None = None

    # Drug-likeness
    qed: float | None = None
    lipinski_violations: list[str] = field(default_factory=list)
    lipinski_pass: bool = False


def compute_properties(smiles: str) -> MoleculeProperties:
    """Parse SMILES and compute all local RDKit descriptors."""
    props = MoleculeProperties(smiles=smiles)

    if not RDKIT_AVAILABLE:
        props.error = "RDKit not installed"
        return props

    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        props.error = "Invalid SMILES string"
        return props

    props.valid = True

    # Core descriptors
    props.mol_weight = round(Descriptors.ExactMolWt(mol), 3)
    props.logp = round(Descriptors.MolLogP(mol), 3)
    props.hbd = rdMolDescriptors.CalcNumHBD(mol)
    props.hba = rdMolDescriptors.CalcNumHBA(mol)
    props.tpsa = round(Descriptors.TPSA(mol), 3)
    props.rotatable_bonds = rdMolDescriptors.CalcNumRotatableBonds(mol)
    props.qed = round(QED.qed(mol), 4)

    # Lipinski RO5 — industry standard from spec
    violations: list[str] = []
    if props.mol_weight > settings.LIPINSKI_MW_MAX:
        violations.append(f"MW {props.mol_weight:.1f} > {settings.LIPINSKI_MW_MAX}")
    if props.logp > settings.LIPINSKI_LOGP_MAX:
        violations.append(f"LogP {props.logp:.2f} > {settings.LIPINSKI_LOGP_MAX}")
    if props.hbd > settings.LIPINSKI_HBD_MAX:
        violations.append(f"HBD {props.hbd} > {settings.LIPINSKI_HBD_MAX}")
    if props.hba > settings.LIPINSKI_HBA_MAX:
        violations.append(f"HBA {props.hba} > {settings.LIPINSKI_HBA_MAX}")

    props.lipinski_violations = violations
    props.lipinski_pass = len(violations) == 0

    return props


def smiles_to_inchi(smiles: str) -> str | None:
    """Convert SMILES to InChI key for deduplication."""
    if not RDKIT_AVAILABLE:
        return None
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None
    from rdkit.Chem.inchi import MolToInchiKey
    return MolToInchiKey(mol)


def canonicalize(smiles: str) -> str | None:
    """Return canonical SMILES or None if invalid."""
    if not RDKIT_AVAILABLE:
        return None
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None
    return Chem.MolToSmiles(mol)
