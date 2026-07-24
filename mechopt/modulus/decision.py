"""Decision intelligence: ranking, Pareto front, knee point, and explanations.

Pure pandas/numpy over the existing evaluated DataFrame — no new physics.
"""

import numpy as np
import pandas as pd


def rank_candidates(df: pd.DataFrame, priority: str = "balanced") -> pd.DataFrame:
    """Return df with a 'rank' column (1-indexed), sorted by priority.

    Only safe candidates get ranked; unsafe rows get rank=NaN.

    Priorities:
        "lightest" → sort safe by weight ascending
        "cheapest" → sort safe by cost ascending
        "safest"   → sort safe by fos descending
        "balanced" → sort safe by normalized (weight + cost) score ascending
                     (same formula as optimizer.recommend)

    Returns a copy of df with 'rank' column added, safe rows first (sorted),
    then unsafe rows (unsorted).
    """
    out = df.copy()
    safe = out[out["safe"]].copy()
    unsafe = out[~out["safe"]].copy()

    if safe.empty:
        out["rank"] = np.nan
        return out

    if priority == "lightest":
        safe = safe.sort_values("weight", ascending=True)
    elif priority == "cheapest":
        safe = safe.sort_values("cost", ascending=True)
    elif priority == "safest":
        safe = safe.sort_values("fos", ascending=False)
    elif priority == "balanced":
        w_norm = (safe["weight"] - safe["weight"].min()) / (
            safe["weight"].max() - safe["weight"].min() + 1e-12
        )
        c_norm = (safe["cost"] - safe["cost"].min()) / (
            safe["cost"].max() - safe["cost"].min() + 1e-12
        )
        score = w_norm + c_norm
        safe = safe.loc[score.sort_values().index]
    else:
        raise ValueError(f"Unknown priority: {priority}")

    safe["rank"] = np.arange(1, len(safe) + 1)
    unsafe["rank"] = np.nan

    return pd.concat([safe, unsafe], ignore_index=False)


def pareto_front(df: pd.DataFrame, objectives: list = None) -> pd.DataFrame:
    """Return non-dominated candidates from the safe subset.

    Default objectives: [("weight", "min"), ("cost", "min")]

    A candidate is dominated if another candidate is <= on ALL objectives
    (respecting direction) and strictly < on at least one.

    Returns a DataFrame subset of the safe, non-dominated rows.
    """
    if objectives is None:
        objectives = [("weight", "min"), ("cost", "min")]

    safe = df[df["safe"]].copy()
    if safe.empty:
        return safe

    # Extract objective values, flipping sign for "max" objectives
    cols = []
    for col, direction in objectives:
        if direction == "max":
            cols.append(-safe[col].values)
        else:
            cols.append(safe[col].values)

    vals = np.column_stack(cols)
    n = len(vals)
    is_dominated = np.zeros(n, dtype=bool)

    for i in range(n):
        if is_dominated[i]:
            continue
        for j in range(n):
            if i == j or is_dominated[j]:
                continue
            # Check if j dominates i: j <= i on all AND j < i on at least one
            if np.all(vals[j] <= vals[i]) and np.any(vals[j] < vals[i]):
                is_dominated[i] = True
                break

    return safe[~is_dominated]


def knee_point(front: pd.DataFrame, objectives: list = None) -> int:
    """Return the DataFrame index of the knee point on the Pareto front.

    Knee = the point closest to the ideal point (min of each objective column
    in the front) in normalized [0,1] space.

    If the front has <= 1 point, return that point's index.
    """
    if objectives is None:
        objectives = [("weight", "min"), ("cost", "min")]

    if len(front) <= 1:
        return front.index[0]

    # Normalize each objective to [0,1]
    cols = []
    for col, direction in objectives:
        values = front[col].values.astype(float)
        if direction == "max":
            values = -values
        col_min = values.min()
        col_max = values.max()
        rng = col_max - col_min
        if rng < 1e-12:
            cols.append(np.zeros(len(values)))
        else:
            cols.append((values - col_min) / rng)

    norm = np.column_stack(cols)
    # Ideal point in normalized space is the origin (0, 0, ...)
    distances = np.sqrt(np.sum(norm**2, axis=1))

    best_idx = np.argmin(distances)
    return front.index[best_idx]


def classify_infeasible(df: pd.DataFrame) -> pd.Series:
    """Return a Series with infeasibility reason for each row.

    Safe rows → "feasible"
    Unsafe rows → pipe-separated failure reasons from safety_case,
    prefixed with "failed_", e.g. "failed_deflection" or
    "failed_bending_stress|failed_deflection"
    """
    reasons = []
    for _, row in df.iterrows():
        if row["safe"]:
            reasons.append("feasible")
        else:
            sc = row["safety_case"]
            if sc.failure_reasons:
                reasons.append("|".join(f"failed_{r}" for r in sc.failure_reasons))
            else:
                reasons.append("infeasible")
    return pd.Series(reasons, index=df.index)


def explain_winner(row: pd.Series) -> str:
    """Return a natural-language explanation of why this candidate wins.

    Uses the safety_case to identify what controls and what has margin.
    """
    sc = row["safety_case"]
    controlling = sc.controlling_check
    controlling_label = controlling.replace("_", " ")

    modeled = [c for c in sc.checks if c.status.value != "not_modeled"]
    if not modeled:
        return f"Selected design. Controlling constraint: {controlling_label}."

    ctrl_check = next((c for c in modeled if c.name == controlling), modeled[0])
    most_margin = max(modeled, key=lambda c: c.margin)
    least_utilized = most_margin.name.replace("_", " ")

    return (
        f"Wins because {controlling_label} is the active constraint "
        f"(margin {ctrl_check.margin:.1%}), "
        f"while {least_utilized} has the most headroom."
    )
