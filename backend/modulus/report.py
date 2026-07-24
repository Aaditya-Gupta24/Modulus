"""Report export module — CSV, JSON, plain-text, and PDF summaries.

Milestone G: produce reproducible, human-readable output from any
Modulus analysis session. No new physics; pure presentation layer.
"""

import csv
import io
import json
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from .design_review import DesignReview
from .failure_modes import Status


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_DIVIDER = "=" * 63


def _safe_cols(df: pd.DataFrame) -> list:
    """Return column names with 'safety_case' excluded."""
    return [c for c in df.columns if c != "safety_case"]


def _to_native(val):
    """Convert numpy scalar types to Python native types for JSON serialisation."""
    if isinstance(val, (np.integer,)):
        return int(val)
    if isinstance(val, (np.floating,)):
        return float(val)
    if isinstance(val, (np.bool_,)):
        return bool(val)
    if isinstance(val, float) and (val != val):   # nan
        return None
    return val


def _df_to_records(df: pd.DataFrame) -> list:
    """Convert df (safety_case excluded) to a list of plain-Python dicts."""
    cols = _safe_cols(df)
    records = []
    for _, row in df[cols].iterrows():
        records.append({k: _to_native(v) for k, v in row.items()})
    return records


def _review_to_dict(review: DesignReview) -> dict:
    """Serialise a DesignReview to a plain-Python dict."""
    sensitivities = []
    for s in review.sensitivities:
        sensitivities.append({
            "parameter": s.parameter,
            "baseline_value": _to_native(s.baseline_value),
            "bumped_value": _to_native(s.bumped_value),
            "fos_change": _to_native(s.fos_change),
            "deflection_change": _to_native(s.deflection_change),
        })
    return {
        "recommended": review.recommended,
        "why_it_won": review.why_it_won,
        "controlling_constraint": review.controlling_constraint,
        "controlling_margin": _to_native(review.controlling_margin),
        "sensitivities": sensitivities,
        "most_important_sensitivity": review.most_important_sensitivity,
        "unmodeled_risks": review.unmodeled_risks,
        "nearest_alternative": review.nearest_alternative,
        "recommended_next_step": review.recommended_next_step,
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def export_csv(df: pd.DataFrame, filepath: str) -> str:
    """Export the evaluated DataFrame to a CSV file.

    The 'safety_case' column is excluded because it contains Python objects
    that are not CSV-serialisable.

    Parameters
    ----------
    df : pd.DataFrame
        Evaluated DataFrame from optimizer.evaluate_candidates.
    filepath : str
        Destination file path (created or overwritten).

    Returns
    -------
    str
        The filepath that was written.
    """
    cols = _safe_cols(df)
    df[cols].to_csv(filepath, index=False)
    return filepath


def export_json(df: pd.DataFrame, review: DesignReview, filepath: str) -> str:
    """Export a JSON report containing candidates and a design review summary.

    The 'safety_case' column is excluded from the candidates list.

    Parameters
    ----------
    df : pd.DataFrame
        Evaluated DataFrame from optimizer.evaluate_candidates.
    review : DesignReview
        Design review produced by design_review.generate_review.
    filepath : str
        Destination file path (created or overwritten).

    Returns
    -------
    str
        The filepath that was written.
    """
    payload = {
        "generated": datetime.now(timezone.utc).isoformat(),
        "candidates": _df_to_records(df),
        "review": _review_to_dict(review),
    }
    with open(filepath, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2, ensure_ascii=False)
    return filepath


def generate_text_report(
    df: pd.DataFrame,
    review: DesignReview,
    problem: dict,
    priority: str,
) -> str:
    """Generate a plain-text design screening report.

    Parameters
    ----------
    df : pd.DataFrame
        Evaluated DataFrame from optimizer.evaluate_candidates (must include
        a 'rank' column, as returned by decision.rank_candidates).
    review : DesignReview
        Design review produced by design_review.generate_review.
    problem : dict
        Keys: load, length, load_case, fos_target, deflection_limit.
    priority : str
        Ranking priority used (e.g. "balanced", "lightest").

    Returns
    -------
    str
        Multi-line report string ready to write to a file or display.
    """
    lines = []

    def _line(s=""):
        lines.append(s)

    # Header
    _line(_DIVIDER)
    _line("Modulus Design Screening Report")
    _line(_DIVIDER)
    _line()

    # 1. Problem definition
    defl_limit = problem.get("deflection_limit")
    defl_str = f"{defl_limit} m" if defl_limit is not None else "None"

    _line("1. PROBLEM DEFINITION")
    _line(f"   Load:             {problem.get('load', 0)} N")
    _line(f"   Span:             {problem.get('length', 0)} m")
    _line(f"   Load case:        {problem.get('load_case', 'N/A')}")
    _line(f"   Target FoS:       {problem.get('fos_target', 1.5)}")
    _line(f"   Deflection limit: {defl_str}")
    _line()

    # 2. Assumptions
    _line("2. ASSUMPTIONS")
    _line("   - Linear-elastic material behaviour")
    _line("   - Static loading only (no dynamic/fatigue effects)")
    _line("   - Prismatic beam (uniform cross-section along span)")
    _line("   - Small deflection theory")
    _line("   - No stress concentrations, weld factors, or joint details")
    _line()

    # 3. Candidate summary
    n_total = len(df)
    n_safe = int(df["safe"].sum())
    _line("3. CANDIDATE SUMMARY")
    _line(f"   Total candidates: {n_total}")
    _line(f"   Safe candidates:  {n_safe}")
    _line()

    # 4. Top-5 ranked candidates table
    _line(f"4. TOP CANDIDATES ({priority})")

    if "rank" in df.columns:
        ranked = df[df["safe"] & df["rank"].notna()].copy()
        ranked = ranked.sort_values("rank")
        top5 = ranked.head(5)
    else:
        top5 = df[df["safe"]].head(5)

    # Table header
    _line(
        f"   {'#':<3} {'Material':<20} {'Section':<16} {'Dims':<18}"
        f"{'FoS':>6}  {'Mass(kg)':>8}  {'Cost($)':>8}"
    )
    _line("   " + "-" * 83)
    for i, (_, row) in enumerate(top5.iterrows(), start=1):
        rank_label = str(int(row["rank"])) if "rank" in top5.columns and not pd.isna(row.get("rank")) else str(i)
        _line(
            f"   {rank_label:<3} {str(row['material']):<20} {str(row['section']):<16}"
            f" {str(row['dims']):<18}"
            f"{row['fos']:>6.2f}  {row['weight']:>8.3f}  {row['cost']:>8.2f}"
        )
    _line()

    # 5. Recommended design
    _line("5. RECOMMENDED DESIGN")
    _line(f"   {review.recommended}")
    _line(f"   Why: {review.why_it_won}")
    _line(
        f"   Controlling: {review.controlling_constraint}"
        f" (margin {review.controlling_margin:.1%})"
    )
    if review.nearest_alternative:
        _line(f"   Nearest alternative: {review.nearest_alternative}")
    _line(f"   Next step: {review.recommended_next_step}")
    _line()

    # 6. Failure-mode table (from the winning design's safety_case)
    _line("6. FAILURE-MODE TABLE")
    winner_rows = df[df["material"] + " / " + df["section"] + " / " + df["dims"] == review.recommended]
    if not winner_rows.empty:
        sc = winner_rows.iloc[0]["safety_case"]
        _line(
            f"   {'Check':<20} {'Value':>12}  {'Allowable':>12}  {'Margin':>8}  {'Status':<12}"
        )
        _line("   " + "-" * 72)
        for chk in sc.checks:
            if chk.status is Status.NOT_MODELED:
                status_str = "NOT MODELED"
                value_str = "—"
                allow_str = "—"
                margin_str = "—"
            else:
                status_str = chk.status.value.upper()
                # Decide units by check name
                if chk.name == "bending_stress":
                    value_str = f"{chk.actual / 1e6:.1f} MPa"
                    allow_str = f"{chk.allowable / 1e6:.1f} MPa"
                elif chk.name == "deflection":
                    value_str = f"{chk.actual * 1000:.3f} mm"
                    allow_str = f"{chk.allowable * 1000:.3f} mm"
                elif chk.name == "yield_fos":
                    value_str = f"{chk.actual:.3f}"
                    allow_str = f"{chk.allowable:.3f}"
                elif chk.name == "euler_buckling":
                    value_str = f"{chk.actual:.3f}"
                    allow_str = f"{chk.allowable:.3f}"
                else:
                    value_str = f"{chk.actual:.4g}"
                    allow_str = f"{chk.allowable:.4g}"
                margin_str = f"{chk.margin:.1%}"
            _line(
                f"   {chk.name:<20} {value_str:>12}  {allow_str:>12}  {margin_str:>8}  {status_str:<12}"
            )
    else:
        _line("   (winner not found in DataFrame)")
    _line()

    # 7. Sensitivity analysis
    _line("7. SENSITIVITY ANALYSIS")
    if review.sensitivities:
        _line(
            f"   {'Parameter':<20} {'Baseline':>12}  {'Bumped(+5%)':>12}  {'Delta FoS':>10}"
        )
        _line("   " + "-" * 60)
        for s in review.sensitivities:
            sign = "+" if s.fos_change >= 0 else ""
            _line(
                f"   {s.parameter:<20} {s.baseline_value:>10.4f} m"
                f"  {s.bumped_value:>10.4f} m"
                f"  {sign}{s.fos_change:>8.2f}"
            )
        _line(f"   Most influential parameter: {review.most_important_sensitivity}")
    else:
        _line("   No sensitivity data available.")
    _line()

    # 8. Limitations disclaimer
    unmodeled = ", ".join(review.unmodeled_risks) if review.unmodeled_risks else "none identified"
    _line("8. LIMITATIONS")
    _line("   - This is a first-pass screening tool, not a substitute for detailed FEA")
    _line(f"   - Does not model: {unmodeled}")
    _line("   - Results assume idealised boundary conditions")
    _line("   - Verify all results with a qualified engineer before fabrication")
    _line()

    # Footer
    _line(_DIVIDER)
    _line(f"Generated by Modulus  |  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    _line(_DIVIDER)

    return "\n".join(lines)


def export_pdf_bytes(
    df: pd.DataFrame,
    review: DesignReview,
    problem: dict,
    priority: str,
) -> bytes:
    """Generate a professional PDF design-screening report and return it as bytes.

    Parameters
    ----------
    df : pd.DataFrame
        Evaluated DataFrame (with 'rank' column if available).
    review : DesignReview
        Design review from design_review.generate_review.
    problem : dict
        Keys: load, length, load_case, fos_target, deflection_limit.
    priority : str
        Ranking priority label (e.g. "balanced", "lightest").

    Returns
    -------
    bytes
        Raw PDF bytes.
    """
    # Late import — reportlab is an optional dependency.
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import mm
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
            HRFlowable, KeepTogether,
        )
        from reportlab.platypus import PageTemplate, Frame
        from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    except ImportError as exc:
        raise ImportError(
            "reportlab is required for PDF export. Install it with: pip install reportlab"
        ) from exc

    # -----------------------------------------------------------------------
    # Styles
    # -----------------------------------------------------------------------
    PAGE_W, PAGE_H = A4
    MARGIN = 20 * mm

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "ReportTitle",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=22,
        leading=28,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#1a1a2e"),
        spaceAfter=6,
    )
    subtitle_style = ParagraphStyle(
        "ReportSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=11,
        leading=14,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#4a4a6a"),
        spaceAfter=4,
    )
    section_header_style = ParagraphStyle(
        "SectionHeader",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=16,
        textColor=colors.HexColor("#1a1a2e"),
        spaceBefore=14,
        spaceAfter=4,
    )
    body_style = ParagraphStyle(
        "Body",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#222222"),
        spaceAfter=3,
    )
    label_style = ParagraphStyle(
        "Label",
        parent=body_style,
        fontName="Helvetica-Bold",
        fontSize=9,
    )
    disclaimer_style = ParagraphStyle(
        "Disclaimer",
        parent=body_style,
        fontSize=8,
        textColor=colors.HexColor("#666666"),
        leading=11,
    )

    # Alternating table row colours
    ROW_EVEN = colors.HexColor("#f0f4ff")
    ROW_ODD = colors.white
    HEADER_BG = colors.HexColor("#1a1a2e")
    HEADER_FG = colors.white

    def _table_style(n_data_rows):
        """Return a TableStyle for a data table with n_data_rows data rows."""
        ts = [
            # Header row
            ("BACKGROUND", (0, 0), (-1, 0), HEADER_BG),
            ("TEXTCOLOR", (0, 0), (-1, 0), HEADER_FG),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 8),
            ("ALIGN", (0, 0), (-1, 0), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 5),
            ("TOPPADDING", (0, 0), (-1, 0), 5),
            # Data rows
            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 1), (-1, -1), 8),
            ("ALIGN", (0, 1), (-1, -1), "CENTER"),
            ("BOTTOMPADDING", (0, 1), (-1, -1), 3),
            ("TOPPADDING", (0, 1), (-1, -1), 3),
            # Grid
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cccccc")),
            ("LINEBELOW", (0, 0), (-1, 0), 1.0, colors.HexColor("#1a1a2e")),
        ]
        # Alternating row colours
        for row in range(1, n_data_rows + 1):
            bg = ROW_EVEN if row % 2 == 0 else ROW_ODD
            ts.append(("BACKGROUND", (0, row), (-1, row), bg))
        return TableStyle(ts)

    # -----------------------------------------------------------------------
    # Page footer callback
    # -----------------------------------------------------------------------
    gen_time = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    def _footer(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 7)
        canvas.setFillColor(colors.HexColor("#888888"))
        footer_text = f"Generated by Modulus  |  {gen_time}"
        canvas.drawString(MARGIN, 10 * mm, footer_text)
        page_text = f"Page {doc.page}"
        canvas.drawRightString(PAGE_W - MARGIN, 10 * mm, page_text)
        canvas.restoreState()

    # -----------------------------------------------------------------------
    # Build story
    # -----------------------------------------------------------------------
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=MARGIN,
        bottomMargin=18 * mm,
    )

    story = []
    content_width = PAGE_W - 2 * MARGIN

    def _section(title):
        story.append(Spacer(1, 6))
        story.append(Paragraph(title, section_header_style))
        story.append(HRFlowable(
            width="100%", thickness=1,
            color=colors.HexColor("#1a1a2e"),
            spaceAfter=6,
        ))

    def _kv(label, value):
        story.append(Paragraph(
            f"<b>{label}:</b>  {value}",
            body_style,
        ))

    # --- Title page block ---
    story.append(Spacer(1, 10 * mm))
    story.append(Paragraph("Modulus Design Screening Report", title_style))
    story.append(Paragraph(gen_time, subtitle_style))
    story.append(Spacer(1, 4 * mm))
    story.append(HRFlowable(
        width="100%", thickness=2,
        color=colors.HexColor("#1a1a2e"),
        spaceAfter=10,
    ))

    # --- 1. Problem Definition ---
    _section("1. Problem Definition")
    defl_limit = problem.get("deflection_limit")
    defl_str = f"{defl_limit * 1000:.1f} mm" if defl_limit is not None else "Not specified"
    _kv("Applied load", f"{problem.get('load', 0):.1f} N")
    _kv("Beam span", f"{problem.get('length', 0):.3f} m")
    _kv("Load case", str(problem.get("load_case", "N/A")).replace("_", " ").title())
    _kv("Target FoS", str(problem.get("fos_target", 1.5)))
    _kv("Deflection limit", defl_str)
    _kv("Optimisation priority", priority.capitalize())

    # --- 2. Recommended Design ---
    _section("2. Recommended Design")
    _kv("Design", review.recommended)
    _kv("Why it won", review.why_it_won)
    _kv("Controlling constraint", review.controlling_constraint.replace("_", " ").title())
    _kv("Controlling margin", f"{review.controlling_margin:.1%}")
    if review.nearest_alternative:
        _kv("Nearest alternative", review.nearest_alternative)
    _kv("Recommended next step", review.recommended_next_step)

    # Winner detail from DataFrame
    winner_mask = (
        df["material"] + " / " + df["section"] + " / " + df["dims"]
        == review.recommended
    )
    winner_rows = df[winner_mask]
    if not winner_rows.empty:
        w = winner_rows.iloc[0]
        story.append(Spacer(1, 3))
        detail_data = [
            ["Stress (MPa)", "Deflection (mm)", "FoS", "Weight (kg)", "Cost ($)"],
            [
                f"{w['stress'] / 1e6:.2f}",
                f"{w['deflection'] * 1000:.3f}",
                f"{w['fos']:.3f}",
                f"{w['weight']:.4f}",
                f"{w['cost']:.3f}",
            ],
        ]
        detail_col_w = [content_width / 5] * 5
        detail_table = Table(detail_data, colWidths=detail_col_w)
        detail_table.setStyle(_table_style(1))
        story.append(detail_table)

    # --- 3. Candidate Summary (top 10) ---
    _section("3. Candidate Summary (Top 10 Safe Designs)")
    if "rank" in df.columns:
        ranked = df[df["safe"] & df["rank"].notna()].copy()
        ranked = ranked.sort_values("rank")
        top10 = ranked.head(10)
    else:
        top10 = df[df["safe"]].head(10)

    if not top10.empty:
        cand_header = [
            "#", "Material", "Section", "Dims",
            "Stress\n(MPa)", "Defl.\n(mm)", "FoS",
            "Weight\n(kg)", "Cost\n($)", "Safe",
        ]
        cand_rows = []
        for i, (_, row) in enumerate(top10.iterrows(), start=1):
            rank_lbl = (
                str(int(row["rank"]))
                if "rank" in top10.columns and not pd.isna(row.get("rank"))
                else str(i)
            )
            cand_rows.append([
                rank_lbl,
                str(row["material"]),
                str(row["section"]),
                str(row["dims"]),
                f"{row['stress'] / 1e6:.1f}",
                f"{row['deflection'] * 1000:.2f}",
                f"{row['fos']:.2f}",
                f"{row['weight']:.3f}",
                f"{row['cost']:.2f}",
                "Yes" if row["safe"] else "No",
            ])

        cand_col_w = [
            0.04 * content_width,  # rank
            0.14 * content_width,  # material
            0.11 * content_width,  # section
            0.15 * content_width,  # dims
            0.08 * content_width,  # stress
            0.08 * content_width,  # deflection
            0.07 * content_width,  # fos
            0.09 * content_width,  # weight
            0.08 * content_width,  # cost
            0.06 * content_width,  # safe
        ]
        cand_table = Table(
            [cand_header] + cand_rows,
            colWidths=cand_col_w,
            repeatRows=1,
        )
        ts = _table_style(len(cand_rows))
        # Colour safe/unsafe in last column
        for row_idx, (_, row) in enumerate(top10.iterrows(), start=1):
            cell_colour = (
                colors.HexColor("#d4edda") if row["safe"]
                else colors.HexColor("#f8d7da")
            )
            ts.add("BACKGROUND", (-1, row_idx), (-1, row_idx), cell_colour)
        cand_table.setStyle(ts)
        story.append(cand_table)
    else:
        story.append(Paragraph("No safe candidates found.", body_style))

    # --- 4. Failure-Mode Table ---
    _section("4. Failure-Mode Table (Winning Design)")
    if not winner_rows.empty:
        sc = winner_rows.iloc[0]["safety_case"]
        fm_header = ["Check", "Value", "Allowable", "Margin", "Status"]
        fm_rows = []
        for chk in sc.checks:
            if chk.status is Status.NOT_MODELED:
                fm_rows.append([
                    chk.name.replace("_", " ").title(),
                    "—", "—", "—", "NOT MODELED",
                ])
            else:
                if chk.name == "bending_stress":
                    val_str = f"{chk.actual / 1e6:.2f} MPa"
                    allow_str = f"{chk.allowable / 1e6:.2f} MPa"
                elif chk.name == "deflection":
                    val_str = f"{chk.actual * 1000:.3f} mm"
                    allow_str = f"{chk.allowable * 1000:.3f} mm"
                elif chk.name in ("yield_fos", "euler_buckling"):
                    val_str = f"{chk.actual:.3f}"
                    allow_str = f"{chk.allowable:.3f}"
                else:
                    val_str = f"{chk.actual:.4g}"
                    allow_str = f"{chk.allowable:.4g}"
                fm_rows.append([
                    chk.name.replace("_", " ").title(),
                    val_str,
                    allow_str,
                    f"{chk.margin:.1%}",
                    chk.status.value.upper(),
                ])

        fm_col_w = [
            0.25 * content_width,
            0.20 * content_width,
            0.20 * content_width,
            0.15 * content_width,
            0.20 * content_width,
        ]
        fm_table = Table([fm_header] + fm_rows, colWidths=fm_col_w)
        fm_ts = _table_style(len(fm_rows))
        # Colour status cells
        _status_colours = {
            "PASS": colors.HexColor("#d4edda"),
            "FAIL": colors.HexColor("#f8d7da"),
            "WARNING": colors.HexColor("#fff3cd"),
            "NOT MODELED": colors.HexColor("#e2e3e5"),
        }
        for row_idx, chk in enumerate(sc.checks, start=1):
            status_str = (
                "NOT MODELED"
                if chk.status is Status.NOT_MODELED
                else chk.status.value.upper()
            )
            cell_col = _status_colours.get(status_str, ROW_ODD)
            fm_ts.add("BACKGROUND", (-1, row_idx), (-1, row_idx), cell_col)
        fm_table.setStyle(fm_ts)
        story.append(fm_table)
    else:
        story.append(Paragraph("Winner not found in DataFrame.", body_style))

    # --- 5. Sensitivity Analysis ---
    _section("5. Sensitivity Analysis")
    if review.sensitivities:
        _kv("Most influential parameter", review.most_important_sensitivity)
        story.append(Spacer(1, 4))
        sens_header = ["Parameter", "Baseline (m)", "Bumped +5% (m)", "Delta FoS", "Delta Defl. (mm)"]
        sens_rows = []
        for s in review.sensitivities:
            sign_fos = "+" if s.fos_change >= 0 else ""
            sign_d = "+" if s.deflection_change >= 0 else ""
            sens_rows.append([
                s.parameter,
                f"{s.baseline_value:.5f}",
                f"{s.bumped_value:.5f}",
                f"{sign_fos}{s.fos_change:.3f}",
                f"{sign_d}{s.deflection_change * 1000:.4f}",
            ])
        sens_col_w = [content_width / 5] * 5
        sens_table = Table([sens_header] + sens_rows, colWidths=sens_col_w)
        sens_table.setStyle(_table_style(len(sens_rows)))
        story.append(sens_table)
    else:
        story.append(Paragraph("No sensitivity data available.", body_style))

    # --- 6. Limitations Disclaimer ---
    _section("6. Limitations & Disclaimer")
    unmodeled = (
        ", ".join(review.unmodeled_risks)
        if review.unmodeled_risks
        else "none identified"
    )
    disclaimers = [
        "This report is produced by Modulus, a first-pass mechanical design screening tool "
        "intended for educational and conceptual-design purposes only.",
        "It is NOT a substitute for detailed finite-element analysis or the judgement of a "
        "qualified structural or mechanical engineer.",
        f"Effects not modelled in this run: {unmodeled}.",
        "Results assume idealised boundary conditions, linear-elastic material behaviour, "
        "static loading only (no dynamic/fatigue effects), prismatic uniform cross-sections, "
        "small-deflection theory, and no stress concentrations, weld factors, or joint details.",
        "All results must be independently verified before use in any fabrication, "
        "construction, or safety-critical application.",
    ]
    for d in disclaimers:
        story.append(Paragraph(d, disclaimer_style))
        story.append(Spacer(1, 3))

    # -----------------------------------------------------------------------
    # Build PDF
    # -----------------------------------------------------------------------
    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return buf.getvalue()


def export_report_bytes(
    df: pd.DataFrame,
    review: DesignReview,
    problem: dict,
    priority: str,
    fmt: str = "csv",
) -> bytes:
    """Return report bytes for a given format — suitable for HTTP download responses.

    Parameters
    ----------
    df : pd.DataFrame
        Evaluated DataFrame (with 'rank' column if available).
    review : DesignReview
        Design review from design_review.generate_review.
    problem : dict
        Keys: load, length, load_case, fos_target, deflection_limit.
    priority : str
        Ranking priority label (used in text header).
    fmt : str
        One of "csv", "json", "text", or "pdf".

    Returns
    -------
    bytes
        Encoded bytes of the requested format (UTF-8 for text formats, raw
        binary for PDF).

    Raises
    ------
    ValueError
        If fmt is not one of the supported values.
    """
    if fmt == "csv":
        buf = io.StringIO()
        cols = _safe_cols(df)
        df[cols].to_csv(buf, index=False)
        return buf.getvalue().encode("utf-8")

    if fmt == "json":
        payload = {
            "generated": datetime.now(timezone.utc).isoformat(),
            "candidates": _df_to_records(df),
            "review": _review_to_dict(review),
        }
        return json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8")

    if fmt == "text":
        report_str = generate_text_report(df, review, problem, priority)
        return report_str.encode("utf-8")

    if fmt == "pdf":
        return export_pdf_bytes(df, review, problem, priority)

    raise ValueError(
        f"Unsupported format '{fmt}'. Choose one of: 'csv', 'json', 'text', 'pdf'."
    )
