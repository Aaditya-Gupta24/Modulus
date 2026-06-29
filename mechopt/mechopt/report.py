"""Report export module — CSV, JSON, and plain-text summaries.

Milestone G: produce reproducible, human-readable output from any
MechOpt analysis session. No new physics; pure presentation layer.
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
    _line("MechOpt Design Screening Report")
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
    _line(f"Generated by MechOpt  |  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    _line(_DIVIDER)

    return "\n".join(lines)


def export_report_bytes(
    df: pd.DataFrame,
    review: DesignReview,
    problem: dict,
    priority: str,
    fmt: str = "csv",
) -> bytes:
    """Return report bytes for a given format — suitable for Streamlit download buttons.

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
        One of "csv", "json", or "text".

    Returns
    -------
    bytes
        UTF-8 encoded bytes of the requested format.

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

    raise ValueError(
        f"Unsupported format '{fmt}'. Choose one of: 'csv', 'json', 'text'."
    )
