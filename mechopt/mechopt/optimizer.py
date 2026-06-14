"""Design-space sweep and recommendation logic.

Strategy: brute-force. Enumerate every (material, section, dimension) candidate,
evaluate each, keep the SAFE ones (FoS >= target), then pick winners by
different objectives. No scipy optimizer needed for a space this small.

IMPLEMENT THESE. See SPEC.md for the expected DataFrame columns and the
definition of each "winner".
"""

import pandas as pd


def evaluate_candidates(load: float, length: float, load_case: str,
                        fos_target: float) -> pd.DataFrame:
    """Sweep the design space and return ONE row per candidate design.

    Required columns (exact names):
        material, section, dims, area, I, weight, cost,
        stress, deflection, fos, safe

    'dims' is a human-readable string of the geometry (e.g. "30x30 mm").
    'safe' is a bool: fos >= fos_target.
    """
    raise NotImplementedError


def recommend(df: pd.DataFrame, priority: str = "balanced") -> pd.Series:
    """Return the single recommended design (a row) from the SAFE candidates.

    priority:
        "lightest" -> min weight among safe
        "cheapest" -> min cost among safe
        "safest"   -> max fos among safe
        "balanced" -> min of a normalized (weight + cost) score among safe

    Raise ValueError if no safe candidate exists.
    """
    raise NotImplementedError
