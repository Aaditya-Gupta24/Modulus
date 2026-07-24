"""Design Review Mode -- a structured review of the recommended design.

A text/presentation layer over the existing failure_modes, decision, and
beam modules. No new physics -- just assembles existing data into a
junior-engineer-level design review.
"""

import re
from dataclasses import dataclass
from typing import List, Optional

import pandas as pd

from . import beam
from .failure_modes import Status
from .decision import rank_candidates, explain_winner
from .materials import MATERIALS
from .optimizer import _section_config


@dataclass
class SensitivityResult:
    parameter: str           # e.g. "height +5%"
    baseline_value: float    # original dimension value
    bumped_value: float      # bumped dimension value
    fos_change: float        # change in FoS (bumped - baseline)
    deflection_change: float  # change in deflection in m (bumped - baseline)


@dataclass
class DesignReview:
    recommended: str
    why_it_won: str
    controlling_constraint: str
    controlling_margin: float
    sensitivities: List[SensitivityResult]
    most_important_sensitivity: str
    unmodeled_risks: List[str]
    nearest_alternative: Optional[str]
    recommended_next_step: str


def _mat_key_from_name(name):
    """Find material key from its display name."""
    for k, v in MATERIALS.items():
        if v.name == name:
            return k
    return None


def _parse_primary_dimension(dims_str):
    """Extract the primary dimension in mm from a dims string like '30x30 mm' or 'd=30 mm'."""
    m = re.match(r"(\d+(?:\.\d+)?)", dims_str)
    if m:
        return float(m.group(1))
    return 30.0  # fallback


def _param_name(sec_type, index):
    """Human-readable parameter name for each section's dimension index."""
    names = {
        "rectangle": ["width/height"],
        "circle": ["diameter"],
        "i_beam": ["flange width", "height", "flange thickness", "web thickness"],
        "square_tube": ["side length", "wall thickness"],
        "hollow_rectangle": ["width", "height", "wall thickness"],
        "hollow_circle": ["outer diameter", "inner diameter"],
    }
    params = names.get(sec_type, [f"dim_{index}"])
    return params[index] if index < len(params) else f"dim_{index}"


def _compute_sensitivities(winner, load, length, load_case, mat):
    """Bump each dimension +5% and measure FoS/deflection change."""
    sec_type = winner["section"]
    baseline_fos = winner["fos"]
    baseline_defl = winner["deflection"]

    d_mm = _parse_primary_dimension(winner["dims"])
    d = d_mm / 1000.0

    config = _section_config(sec_type, d, d_mm)
    if config is None:
        return []

    sec_fn, sec_dims, _ = config

    results = []
    for i, dim_val in enumerate(sec_dims):
        bumped_dims = list(sec_dims)
        bumped_dims[i] = dim_val * 1.05
        bumped_dims = tuple(bumped_dims)

        try:
            props = sec_fn(*bumped_dims)
            M = beam.max_moment(load, length, load_case)
            sigma = beam.max_stress(M, props)
            delta = beam.max_deflection(load, length, mat.E, props, load_case)
            fos = beam.factor_of_safety(sigma, mat.sigma_y)

            results.append(SensitivityResult(
                parameter=_param_name(sec_type, i),
                baseline_value=dim_val,
                bumped_value=dim_val * 1.05,
                fos_change=fos - baseline_fos,
                deflection_change=delta - baseline_defl,
            ))
        except (ValueError, ZeroDivisionError):
            pass

    return results


def _next_step(controlling):
    """Return recommended next step based on the controlling constraint."""
    steps = {
        "deflection": (
            "Increase section depth or switch to a stiffer material "
            "(higher E) to reduce deflection."
        ),
        "bending_stress": (
            "Increase section size or switch to a stronger material "
            "(higher \u03c3y) to reduce stress."
        ),
        "euler_buckling": (
            "Increase section moment of inertia or reduce unsupported "
            "length to improve buckling resistance."
        ),
        "yield_fos": (
            "Increase section size or choose a higher-yield material "
            "to improve factor of safety."
        ),
    }
    return steps.get(
        controlling,
        "Review the controlling constraint and consider adjusting "
        "geometry or material.",
    )


def generate_review(winner: pd.Series, df: pd.DataFrame,
                    priority: str = "balanced",
                    load: float = 0, length: float = 0,
                    load_case: str = "cantilever_end",
                    fos_target: float = 1.5,
                    deflection_limit: float = None) -> DesignReview:
    """Generate a structured design review for the winning candidate.

    Parameters
    ----------
    winner : pd.Series
        Row from the evaluated DataFrame (the recommended design).
    df : pd.DataFrame
        Full evaluated DataFrame from optimizer.evaluate_candidates.
    priority : str
        Ranking priority passed to rank_candidates.
    load : float
        Applied load [N].
    length : float
        Beam span [m].
    load_case : str
        "cantilever_end" or "simply_center".
    fos_target : float
        Required factor of safety (default 1.5).
    deflection_limit : float or None
        Maximum allowable deflection [m].

    Returns
    -------
    DesignReview
    """
    # 1. recommended label
    recommended = f"{winner['material']} / {winner['section']} / {winner['dims']}"

    # 2. why it won
    why_it_won = explain_winner(winner)

    # 3. controlling constraint and margin
    sc = winner["safety_case"]
    controlling_constraint = sc.controlling_check
    controlling_margin = 0.0
    for check in sc.checks:
        if check.name == controlling_constraint:
            controlling_margin = check.margin
            break

    # 4. sensitivities
    mat_key = _mat_key_from_name(winner["material"])
    mat = MATERIALS[mat_key] if mat_key else None

    if mat is not None:
        sensitivities = _compute_sensitivities(
            winner, load, length, load_case, mat,
        )
    else:
        sensitivities = []

    # 5. most important sensitivity
    if sensitivities:
        best = max(sensitivities, key=lambda s: abs(s.fos_change))
        most_important_sensitivity = best.parameter
    else:
        most_important_sensitivity = "N/A"

    # 6. unmodeled risks
    unmodeled_risks = [
        c.name for c in sc.checks if c.status is Status.NOT_MODELED
    ]

    # 7. nearest alternative
    ranked = rank_candidates(df, priority)
    safe_ranked = ranked[ranked["safe"]].copy()
    safe_ranked = safe_ranked.sort_values("rank")
    nearest_alternative = None
    if len(safe_ranked) >= 2:
        second = safe_ranked.iloc[1]
        nearest_alternative = (
            f"{second['material']} / {second['section']} / {second['dims']}"
        )

    # 8. recommended next step
    recommended_next_step = _next_step(controlling_constraint)

    return DesignReview(
        recommended=recommended,
        why_it_won=why_it_won,
        controlling_constraint=controlling_constraint,
        controlling_margin=controlling_margin,
        sensitivities=sensitivities,
        most_important_sensitivity=most_important_sensitivity,
        unmodeled_risks=unmodeled_risks,
        nearest_alternative=nearest_alternative,
        recommended_next_step=recommended_next_step,
    )
