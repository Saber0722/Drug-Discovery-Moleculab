"""Molecule ORM model."""

import uuid
from datetime import datetime

from sqlalchemy import String, Float, Text, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Molecule(Base):
    __tablename__ = "molecules"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    smiles: Mapped[str] = mapped_column(Text, nullable=False)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Computed properties (filled by screening service)
    mol_weight: Mapped[float | None] = mapped_column(Float, nullable=True)
    logp: Mapped[float | None] = mapped_column(Float, nullable=True)
    hbd: Mapped[int | None] = mapped_column(nullable=True)
    hba: Mapped[int | None] = mapped_column(nullable=True)
    tpsa: Mapped[float | None] = mapped_column(Float, nullable=True)
    qed: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Verdict
    lipinski_pass: Mapped[bool | None] = mapped_column(nullable=True)
    overall_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    verdict: Mapped[str | None] = mapped_column(String(10), nullable=True)  # PASS/FAIL

    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
