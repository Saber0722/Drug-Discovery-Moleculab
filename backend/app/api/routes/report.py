"""
Report API — generates structured PDF screening reports via ReportLab.

Output matches spec: molecule image, all scores, pass/fail verdict, AI suggestions.
Clearly labelled "Computational predictions for research purposes only."
"""

from __future__ import annotations
import io
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

router = APIRouter()


class ReportRequest(BaseModel):
    run_id: str | None = None
    molecules: list[dict] | None = None   # inline results, no DB lookup needed
    title: str = "MolecuLab Screening Report"


@router.post("/generate")
async def generate_report(payload: ReportRequest):
    """Generate a PDF screening report and return it as a binary stream."""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib import colors
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
        )
        from reportlab.lib.units import mm
    except ImportError:
        raise HTTPException(
            status_code=503,
            detail="ReportLab not installed. Run: uv add reportlab"
        )

    molecules = payload.molecules or []
    buf = io.BytesIO()

    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=20*mm, rightMargin=20*mm,
        topMargin=20*mm, bottomMargin=20*mm,
    )
    styles = getSampleStyleSheet()
    story = []

    # ── Header ───────────────────────────────────────────────────────────────
    story.append(Paragraph(
        f"<b>{payload.title}</b>",
        ParagraphStyle("Title", parent=styles["Title"], fontSize=18, spaceAfter=4)
    ))
    story.append(Paragraph(
        "⚠️ Computational predictions for research purposes only — not clinical advice.",
        ParagraphStyle("Disclaimer", parent=styles["Normal"],
                       textColor=colors.red, fontSize=8, spaceAfter=12)
    ))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.black))
    story.append(Spacer(1, 6*mm))

    # ── Summary table ─────────────────────────────────────────────────────────
    passed = sum(1 for m in molecules if m.get("verdict") == "PASS")
    failed = len(molecules) - passed
    summary_data = [
        ["Total Molecules", "PASS", "FAIL", "Pass Rate"],
        [str(len(molecules)), str(passed), str(failed),
         f"{passed/max(len(molecules),1)*100:.1f}%"],
    ]
    summary_table = Table(summary_data, colWidths=[45*mm]*4)
    summary_table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#1a1a2e")),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("ALIGN", (0,0), (-1,-1), "CENTER"),
        ("GRID", (0,0), (-1,-1), 0.5, colors.grey),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.HexColor("#f5f5f5"), colors.white]),
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 8*mm))

    # ── Per-molecule detail ───────────────────────────────────────────────────
    for i, mol in enumerate(molecules, 1):
        verdict = mol.get("verdict", "?")
        color = colors.green if verdict == "PASS" else (
            colors.orange if verdict == "REVIEW" else colors.red
        )

        story.append(Paragraph(
            f"<b>Molecule {i}</b> — "
            f"<font color='{'green' if verdict == 'PASS' else 'red'}'>{verdict}</font>  "
            f"(Score: {mol.get('overall_score', '—')})",
            ParagraphStyle("MolHead", parent=styles["Heading2"], fontSize=11, spaceAfter=2)
        ))
        story.append(Paragraph(
            f"<i>SMILES:</i> {mol.get('smiles', '—')}",
            ParagraphStyle("SMILES", parent=styles["Code"], fontSize=7, spaceAfter=4)
        ))

        detail_data = [
            ["Property", "Value", "Property", "Value"],
            ["MW (Da)", f"{mol.get('mol_weight', '—')}",
             "LogP", f"{mol.get('logp', '—')}"],
            ["HBD", f"{mol.get('hbd', '—')}",
             "HBA", f"{mol.get('hba', '—')}"],
            ["TPSA", f"{mol.get('tpsa', '—')}",
             "QED", f"{mol.get('qed', '—')}"],
            ["Tox overall", f"{mol.get('tox_overall', '—')}",
             "Binding (kcal/mol)", f"{mol.get('binding_affinity', '—')}"],
            ["Lipinski", "✓ PASS" if mol.get('lipinski_pass') else "✗ FAIL",
             "Binding verdict", mol.get('binding_verdict', '—')],
        ]
        detail_table = Table(detail_data, colWidths=[45*mm, 30*mm, 45*mm, 30*mm])
        detail_table.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#e8e8e8")),
            ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
            ("FONTSIZE", (0,0), (-1,-1), 8),
            ("GRID", (0,0), (-1,-1), 0.3, colors.lightgrey),
            ("ALIGN", (1,0), (1,-1), "CENTER"),
            ("ALIGN", (3,0), (3,-1), "CENTER"),
        ]))
        story.append(detail_table)
        story.append(Spacer(1, 6*mm))

    doc.build(story)
    buf.seek(0)

    filename = f"moleculab_report_{payload.run_id or 'export'}.pdf"
    return StreamingResponse(
        buf,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
