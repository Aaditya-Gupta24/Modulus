"""Design-space sweep and recommendation logic.

Strategy: brute-force. Enumerate every (material, section, dimension) candidate,
evaluate each, keep the SAFE ones (FoS >= target), then pick winners by
different objectives. No scipy optimizer needed for a space this small.
"""

import numpy as np
import pandas as pd

from .materials import MATERIALS
from . import sections, beam, failure_modes


def _section_config(sec_type, d, d_mm):
    """Map (section_type, d) to (section_fn, dims_tuple, dims_string).

    Returns None when the geometry is invalid (fails guard check).
    """
    if sec_type == "rectangle":
        return sections.rectangle, (d, d), f"{d_mm:.0f}x{d_mm:.0f} mm"

    if sec_type == "circle":
        return sections.circle, (d,), f"d={d_mm:.0f} mm"

    if sec_type == "i_beam":
        h = d
        b = d
        tf = d / 10
        tw = d / 10
        if not (h > 2 * tf and b > tw):
            return None
        return (sections.i_beam, (b, h, tf, tw),
                f"{d_mm:.0f}x{d_mm:.0f} tf={d_mm/10:.0f} tw={d_mm/10:.0f} mm")

    if sec_type == "square_tube":
        w = max(d / 10, 0.002)
        if not (2 * w < d):
            return None
        w_mm = w * 1000
        return (sections.square_tube, (d, w),
                f"{d_mm:.0f}x{d_mm:.0f} w={w_mm:.0f} mm")

    if sec_type == "hollow_rectangle":
        w = max(d / 10, 0.002)
        if not (2 * w < d):
            return None
        w_mm = w * 1000
        return (sections.hollow_rectangle, (d, d, w),
                f"{d_mm:.0f}x{d_mm:.0f} w={w_mm:.0f} mm")

    if sec_type == "hollow_circle":
        wall = max(d / 10, 0.002)
        di = d - 2 * wall
        if not (di > 0):
            return None
        di_mm = di * 1000
        return (sections.hollow_circle, (d, di),
                f"d={d_mm:.0f} di={di_mm:.0f} mm")

    return None


def evaluate_candidates(load: float, length: float, load_case: str,
                        fos_target: float, *,
                        material_keys: list = None,
                        section_types: list = None,
                        deflection_limit: float = None) -> pd.DataFrame:
    """Sweep the design space and return ONE row per candidate design.

    Required columns (exact names):
        material, section, dims, area, I, weight, cost,
        stress, deflection, fos, safe

    'dims' is a human-readable string of the geometry (e.g. "30x30 mm").
    'safe' is a bool: fos >= fos_target AND deflection <= deflection_limit (if set).

    Optional filtering:
        material_keys: list of keys from MATERIALS to include (default: all)
        section_types: list of section names to include (default: ["rectangle", "circle"])
        deflection_limit: max allowable deflection in metres (default: None = no limit)
    """
    if material_keys is None:
        material_keys = list(MATERIALS.keys())
    if section_types is None:
        section_types = ["rectangle", "circle"]

    # Buckling effective-length factor depends on load case.
    K = 2.0 if load_case == "cantilever_end" else 1.0

    rows = []
    dims_mm = np.arange(10, 110, 10)  # 10 to 100 mm in steps of 10

    for mat_key in material_keys:
        mat = MATERIALS[mat_key]
        for d_mm in dims_mm:
            d = d_mm / 1000.0
            M = beam.max_moment(load, length, load_case)

            for sec_type in section_types:
                result = _section_config(sec_type, d, d_mm)
                if result is None:
                    continue  # invalid geometry
                sec_fn, sec_dims, dims_str = result

                props = sec_fn(*sec_dims)
                sigma = beam.max_stress(M, props)
                delta = beam.max_deflection(load, length, mat.E, props,
                                            load_case)
                fos = beam.factor_of_safety(sigma, mat.sigma_y)
                weight = props.A * length * mat.rho
                cost = weight * mat.cost
                defl_ok = ((deflection_limit is None)
                           or (delta <= deflection_limit))

                safety_case = failure_modes.evaluate_candidate(
                    material=mat,
                    section_fn=sec_fn,
                    dims=sec_dims,
                    load=load,
                    length=length,
                    load_case=load_case,
                    fos_target=fos_target,
                    deflection_limit=deflection_limit,
                    compression_load=load,
                    K=K,
                )

                rows.append({
                    "material": mat.name,
                    "section": sec_type,
                    "dims": dims_str,
                    "area": props.A,
                    "I": props.I,
                    "weight": weight,
                    "cost": cost,
                    "stress": sigma,
                    "deflection": delta,
                    "fos": fos,
                    "safe": (fos >= fos_target) and defl_ok,
                    "safety_case": safety_case,
                })

    return pd.DataFrame(rows)


def recommend(df: pd.DataFrame, priority: str = "balanced") -> pd.Series:
    """Return the single recommended design (a row) from the SAFE candidates.

    priority:
        "lightest" -> min weight among safe
        "cheapest" -> min cost among safe
        "safest"   -> max fos among safe
        "balanced" -> min of a normalized (weight + cost) score among safe

    Raise ValueError if no safe candidate exists.
    """
    safe = df[df["safe"]]
    if safe.empty:
        raise ValueError("No safe candidate exists.")

    if priority == "lightest":
        return safe.loc[safe["weight"].idxmin()]
    elif priority == "cheapest":
        return safe.loc[safe["cost"].idxmin()]
    elif priority == "safest":
        return safe.loc[safe["fos"].idxmax()]
    elif priority == "balanced":
        w_norm = (safe["weight"] - safe["weight"].min()) / (safe["weight"].max() - safe["weight"].min() + 1e-12)
        c_norm = (safe["cost"] - safe["cost"].min()) / (safe["cost"].max() - safe["cost"].min() + 1e-12)
        score = w_norm + c_norm
        return safe.loc[score.idxmin()]
    else:
        raise ValueError(f"Unknown priority: {priority}")
