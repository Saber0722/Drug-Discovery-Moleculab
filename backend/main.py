"""MolecuLab Backend — FastAPI entrypoint."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.core.config import settings
from app.core.database import init_db
from app.api.routes import molecules, screening, admet, docking, report, ai


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("MolecuLab backend starting up…")
    await init_db()
    yield
    logger.info("MolecuLab backend shutting down.")


app = FastAPI(
    title="MolecuLab API",
    description="Open in-silico drug screening workbench",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ──────────────────────────────────────────────────────────────────
app.include_router(molecules.router, prefix="/api/molecules", tags=["Molecules"])
app.include_router(screening.router, prefix="/api/screening", tags=["Screening"])
app.include_router(admet.router,     prefix="/api/admet",     tags=["ADMET"])
app.include_router(docking.router,   prefix="/api/docking",   tags=["Docking"])
app.include_router(report.router,    prefix="/api/report",    tags=["Report"])
app.include_router(ai.router,        prefix="/api/ai",         tags=["AI"])


@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "0.1.0"}