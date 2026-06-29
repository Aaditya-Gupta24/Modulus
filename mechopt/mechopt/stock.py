"""Standard stock catalogs and nearest-buyable snapping.

Constrains the design sweep to off-the-shelf dimensions and lets the user
compare a theoretical optimum against the nearest purchasable geometry.
"""

import re
from dataclasses import dataclass

import numpy as np

from . import beam, sections
from .materials import MATERIALS


# ── Stock catalogs ──────────────────────────────────────────────────────────

WALL_THICKNESSES_MM = [1, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 10]

STOCK_DIMS_MM = [10, 12, 15, 16, 20, 25, 30, 35, 40, 45, 50, 60, 70, 80, 90, 100]

BOLT_SIZES = ["M3", "M4", "M5", "M6", "M8", "M10"]


# ── Helpers ─────────────────────────────────────────────────────────────────

def _snap(value: float, catalog: list[float]) -> float:
    """Return the catalog entry nearest to *value*."""
    return min(catalog, key=lambda v: abs(v - value))


def stock_dims_mm() -> np.ndarray:
    """Stock dimension array, drop-in replacement for np.arange(10, 110, 10)."""
    return np.array(STOCK_DIMS_MM, dtype=float)


def _material_key_from_name(name: str) -> str:
    """Look up a MATERIALS dict key from the human-readable name."""
    for k, v in MATERIALS.items():
        if v.name == name:
            return k
    raise ValueError(f"Unknown material name: {name}")


def _parse_dims(section: str, dims_str: str) -> dict:
    """Extract numeric dimensions from the dims string produced by the optimizer.

    Returns a dict with at least 'd_mm' and optionally 'w_mm' or 'di_mm'.
    """
    nums = [float(x) for x in re.findall(r"[\d.]+", dims_str)]

    if section == "rectangle":
        return {"d_mm": nums[0]}
    if section == "circle":
        return {"d_mm": nums[0]}
    if section == "i_beam":
        # "30x30 tf=3 tw=3 mm"
        tf = re.search(r"tf=([\d.]+)", dims_str)
        return {"d_mm": nums[0], "w_mm": float(tf.group(1)) if tf else nums[0] / 10}
    if section in ("square_tube", "hollow_rectangle"):
        # "30x30 w=3 mm"
        w = re.search(r"w=([\d.]+)", dims_str)
        return {"d_mm": nums[0], "w_mm": float(w.group(1)) if w else nums[0] / 10}
    if section == "hollow_circle":
        # "d=30 di=24 mm"
        di = re.search(r"di=([\d.]+)", dims_str)
        return {"d_mm": nums[0], "di_mm": float(di.group(1)) if di else nums[0] * 0.8}
    raise ValueError(f"Unknown section type: {section}")


def _build_section(section: str, d: float, w: float = None, di: float = None):
    """Build section props from snapped metric dims (in metres).

    Returns (section_fn, dims_tuple, SectionProps) or None on invalid geometry.
    """
    if section == "rectangle":
        fn, dims = sections.rectangle, (d, d)
    elif section == "circle":
        fn, dims = sections.circle, (d,)
    elif section == "i_beam":
        tf = tw = w
        if not (d > 2 * tf and d > tw):
            return None
        fn, dims = sections.i_beam, (d, d, tf, tw)
    elif section == "square_tube":
        if not (2 * w < d):
            return None
        fn, dims = sections.square_tube, (d, w)
    elif section == "hollow_rectangle":
        if not (2 * w < d):
            return None
        fn, dims = sections.hollow_rectangle, (d, d, w)
    elif section == "hollow_circle":
        if not (di is not None and 0 < di < d):
            return None
        fn, dims = sections.hollow_circle, (d, di)
    else:
        return None

    return fn, dims, fn(*dims)


# ── StockComparison dataclass ───────────────────────────────────────────────

@dataclass(frozen=True)
class StockComparison:
    original: dict
    snapped: dict
    snapped_dims_mm: dict
    mass_penalty_pct: float
    stiffness_change_pct: float
    fos_change: float
    summary: str


# ── Main function ───────────────────────────────────────────────────────────

def nearest_buyable(theoretical, load: float, length: float,
                    load_case: str, fos_target: float,
                    deflection_limit: float = None) -> StockComparison:
    """Snap a theoretical design to the nearest stock size and compare.

    Parameters
    ----------
    theoretical : dict or pd.Series
        One row from evaluate_candidates output.
    load, length, load_case, fos_target, deflection_limit
        Same parameters used in the original sweep.

    Returns
    -------
    StockComparison
    """
    sec_type = theoretical["section"]
    parsed = _parse_dims(sec_type, theoretical["dims"])
    d_mm_orig = parsed["d_mm"]

    # Snap outer dimension
    d_mm_snap = _snap(d_mm_orig, STOCK_DIMS_MM)
    d_snap = d_mm_snap / 1000.0

    snapped_dims = {"d_mm": d_mm_snap}

    # Snap wall / inner dimension
    w_snap = None
    di_snap = None

    if sec_type in ("i_beam", "square_tube", "hollow_rectangle"):
        w_mm_orig = parsed.get("w_mm", d_mm_orig / 10)
        # Filter to walls that produce valid geometry
        valid_walls = [wt for wt in WALL_THICKNESSES_MM if wt < d_mm_snap / 2]
        if not valid_walls:
            valid_walls = [WALL_THICKNESSES_MM[0]]
        w_mm_snap = _snap(w_mm_orig, valid_walls)
        w_snap = w_mm_snap / 1000.0
        snapped_dims["w_mm"] = w_mm_snap

    elif sec_type == "hollow_circle":
        di_mm_orig = parsed.get("di_mm", d_mm_orig * 0.8)
        wall_mm_orig = (d_mm_orig - di_mm_orig) / 2
        valid_walls = [wt for wt in WALL_THICKNESSES_MM
                       if d_mm_snap - 2 * wt > 0]
        if not valid_walls:
            valid_walls = [WALL_THICKNESSES_MM[0]]
        wall_mm_snap = _snap(wall_mm_orig, valid_walls)
        di_mm_snap = d_mm_snap - 2 * wall_mm_snap
        di_snap = di_mm_snap / 1000.0
        snapped_dims["di_mm"] = di_mm_snap
        snapped_dims["wall_mm"] = wall_mm_snap

    # Build snapped section
    result = _build_section(sec_type, d_snap, w=w_snap, di=di_snap)
    if result is None:
        raise ValueError(
            f"Snapped geometry is invalid for {sec_type} with dims {snapped_dims}"
        )
    sec_fn, sec_dims, props = result

    # Recompute performance
    mat_key = _material_key_from_name(theoretical["material"])
    mat = MATERIALS[mat_key]

    M = beam.max_moment(load, length, load_case)
    sigma = beam.max_stress(M, props)
    delta = beam.max_deflection(load, length, mat.E, props, load_case)
    fos = beam.factor_of_safety(sigma, mat.sigma_y)
    weight = props.A * length * mat.rho
    cost = weight * mat.cost
    defl_ok = (deflection_limit is None) or (delta <= deflection_limit)

    orig_weight = theoretical["weight"]
    orig_I = theoretical["I"]
    orig_fos = theoretical["fos"]

    mass_pct = ((weight - orig_weight) / orig_weight) * 100 if orig_weight else 0.0
    stiff_pct = ((props.I - orig_I) / orig_I) * 100 if orig_I else 0.0
    fos_delta = fos - orig_fos

    snapped_row = {
        "material": theoretical["material"],
        "section": sec_type,
        "dims": theoretical["dims"],  # keep original string for reference
        "area": props.A,
        "I": props.I,
        "weight": weight,
        "cost": cost,
        "stress": sigma,
        "deflection": delta,
        "fos": fos,
        "safe": (fos >= fos_target) and defl_ok,
    }

    sign = "+" if mass_pct >= 0 else ""
    summary = (
        f"Stock snap: {d_mm_snap:.0f} mm (was {d_mm_orig:.0f} mm) "
        f"\u2192 Mass {sign}{mass_pct:.1f}%, "
        f"Stiffness {'+' if stiff_pct >= 0 else ''}{stiff_pct:.1f}%, "
        f"FoS {fos:.1f} (was {orig_fos:.1f})"
    )

    return StockComparison(
        original=dict(theoretical),
        snapped=snapped_row,
        snapped_dims_mm=snapped_dims,
        mass_penalty_pct=mass_pct,
        stiffness_change_pct=stiff_pct,
        fos_change=fos_delta,
        summary=summary,
    )
