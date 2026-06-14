"""Design-space sweep and recommendation logic.

Strategy: brute-force. Enumerate every (material, section, dimension) candidate,
evaluate each, keep the SAFE ones (FoS >= target), then pick winners by
different objectives. No scipy optimizer needed for a space this small.
"""

import numpy as np
import pandas as pd

from .materials import MATERIALS
from . import sections, beam


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

    rows = []
    dims_mm = np.arange(10, 110, 10)  # 10 to 100 mm in steps of 10

    for mat_key in material_keys:
        mat = MATERIALS[mat_key]
        for d_mm in dims_mm:
            d = d_mm / 1000.0
            M = beam.max_moment(load, length, load_case)

            if "rectangle" in section_types:
                props = sections.rectangle(d, d)
                sigma = beam.max_stress(M, props)
                delta = beam.max_deflection(load, length, mat.E, props, load_case)
                fos = beam.factor_of_safety(sigma, mat.sigma_y)
                weight = props.A * length * mat.rho
                cost = weight * mat.cost
                defl_ok = (deflection_limit is None) or (delta <= deflection_limit)
                rows.append({
                    "material": mat.name,
                    "section": "rectangle",
                    "dims": f"{d_mm:.0f}x{d_mm:.0f} mm",
                    "area": props.A,
                    "I": props.I,
                    "weight": weight,
                    "cost": cost,
                    "stress": sigma,
                    "deflection": delta,
                    "fos": fos,
                    "safe": (fos >= fos_target) and defl_ok,
                })

            if "circle" in section_types:
                props = sections.circle(d)
                sigma = beam.max_stress(M, props)
                delta = beam.max_deflection(load, length, mat.E, props, load_case)
                fos = beam.factor_of_safety(sigma, mat.sigma_y)
                weight = props.A * length * mat.rho
                cost = weight * mat.cost
                defl_ok = (deflection_limit is None) or (delta <= deflection_limit)
                rows.append({
                    "material": mat.name,
                    "section": "circle",
                    "dims": f"d={d_mm:.0f} mm",
                    "area": props.A,
                    "I": props.I,
                    "weight": weight,
                    "cost": cost,
                    "stress": sigma,
                    "deflection": delta,
                    "fos": fos,
                    "safe": (fos >= fos_target) and defl_ok,
                })

            if "i_beam" in section_types:
                h = d
                b = d
                tf = d / 10
                tw = d / 10
                if h > 2 * tf and b > tw:
                    props = sections.i_beam(b, h, tf, tw)
                    sigma = beam.max_stress(M, props)
                    delta = beam.max_deflection(load, length, mat.E, props, load_case)
                    fos = beam.factor_of_safety(sigma, mat.sigma_y)
                    weight = props.A * length * mat.rho
                    cost = weight * mat.cost
                    defl_ok = (deflection_limit is None) or (delta <= deflection_limit)
                    rows.append({
                        "material": mat.name,
                        "section": "i_beam",
                        "dims": f"{d_mm:.0f}x{d_mm:.0f} tf={d_mm/10:.0f} tw={d_mm/10:.0f} mm",
                        "area": props.A,
                        "I": props.I,
                        "weight": weight,
                        "cost": cost,
                        "stress": sigma,
                        "deflection": delta,
                        "fos": fos,
                        "safe": (fos >= fos_target) and defl_ok,
                    })

            if "square_tube" in section_types:
                w = max(d / 10, 0.002)
                if 2 * w < d:
                    props = sections.square_tube(d, w)
                    sigma = beam.max_stress(M, props)
                    delta = beam.max_deflection(load, length, mat.E, props, load_case)
                    fos = beam.factor_of_safety(sigma, mat.sigma_y)
                    weight = props.A * length * mat.rho
                    cost = weight * mat.cost
                    defl_ok = (deflection_limit is None) or (delta <= deflection_limit)
                    w_mm = w * 1000
                    rows.append({
                        "material": mat.name,
                        "section": "square_tube",
                        "dims": f"{d_mm:.0f}x{d_mm:.0f} w={w_mm:.0f} mm",
                        "area": props.A,
                        "I": props.I,
                        "weight": weight,
                        "cost": cost,
                        "stress": sigma,
                        "deflection": delta,
                        "fos": fos,
                        "safe": (fos >= fos_target) and defl_ok,
                    })

            if "hollow_rectangle" in section_types:
                # Box tube: square outer, wall = d/10 (min 2 mm)
                w = max(d / 10, 0.002)
                if 2 * w < d:
                    props = sections.hollow_rectangle(d, d, w)
                    sigma = beam.max_stress(M, props)
                    delta = beam.max_deflection(load, length, mat.E, props, load_case)
                    fos = beam.factor_of_safety(sigma, mat.sigma_y)
                    weight = props.A * length * mat.rho
                    cost = weight * mat.cost
                    defl_ok = (deflection_limit is None) or (delta <= deflection_limit)
                    w_mm = w * 1000
                    rows.append({
                        "material": mat.name,
                        "section": "hollow_rectangle",
                        "dims": f"{d_mm:.0f}x{d_mm:.0f} w={w_mm:.0f} mm",
                        "area": props.A,
                        "I": props.I,
                        "weight": weight,
                        "cost": cost,
                        "stress": sigma,
                        "deflection": delta,
                        "fos": fos,
                        "safe": (fos >= fos_target) and defl_ok,
                    })

            if "hollow_circle" in section_types:
                # Round tube: wall = d/10 (min 2 mm)
                wall = max(d / 10, 0.002)
                di = d - 2 * wall
                if di > 0:
                    props = sections.hollow_circle(d, di)
                    sigma = beam.max_stress(M, props)
                    delta = beam.max_deflection(load, length, mat.E, props, load_case)
                    fos = beam.factor_of_safety(sigma, mat.sigma_y)
                    weight = props.A * length * mat.rho
                    cost = weight * mat.cost
                    defl_ok = (deflection_limit is None) or (delta <= deflection_limit)
                    di_mm = di * 1000
                    rows.append({
                        "material": mat.name,
                        "section": "hollow_circle",
                        "dims": f"d={d_mm:.0f} di={di_mm:.0f} mm",
                        "area": props.A,
                        "I": props.I,
                        "weight": weight,
                        "cost": cost,
                        "stress": sigma,
                        "deflection": delta,
                        "fos": fos,
                        "safe": (fos >= fos_target) and defl_ok,
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
