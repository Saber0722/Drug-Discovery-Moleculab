"""ScreeningRun ORM model — tracks a multi-molecule batch job."""

import uuid
from datetime import datetime

from sqlalchemy import String, Integer, Text, DateTime, func, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ScreeningRun(Base):
    __tablename__ = "screening_runs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    status: Mapped[str] = mapped_column(String(20), default="pending")
    # pending | running | completed | failed

    total_molecules: Mapped[int] = mapped_column(Integer, default=0)
    passed: Mapped[int] = mapped_column(Integer, default=0)
    failed: Mapped[int] = mapped_column(Integer, default=0)

    target_protein: Mapped[str | None] = mapped_column(String(100), nullable=True)
    celery_task_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # JSON blob: list of molecule result dicts
    results: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
