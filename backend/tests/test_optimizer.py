"""Optimizer / recommendation tests (behavioral, not exact-value)."""

import pytest
from modulus import optimizer

EXPECTED_COLS = {
    "material", "section", "dims", "area", "I", "weight",
    "cost", "stress", "deflection", "fos", "safe",
}


def _df():
    return optimizer.evaluate_candidates(
        load=500.0, length=1.0, load_case="cantilever_end", fos_target=2.0
    )


def test_dataframe_shape_and_columns():
    df = _df()
    assert len(df) > 0
    assert EXPECTED_COLS.issubset(set(df.columns))


def test_safe_flag_matches_target():
    df = _df()
    assert (df["safe"] == (df["fos"] >= 2.0)).all()


def test_lightest_is_min_weight_among_safe():
    df = _df()
    safe = df[df["safe"]]
    rec = optimizer.recommend(df, "lightest")
    assert rec["weight"] == pytest.approx(safe["weight"].min())
    assert bool(rec["safe"]) is True


def test_cheapest_is_min_cost_among_safe():
    df = _df()
    safe = df[df["safe"]]
    rec = optimizer.recommend(df, "cheapest")
    assert rec["cost"] == pytest.approx(safe["cost"].min())


def test_safest_is_max_fos_among_safe():
    df = _df()
    safe = df[df["safe"]]
    rec = optimizer.recommend(df, "safest")
    assert rec["fos"] == pytest.approx(safe["fos"].max())


import pandas as pd

def test_no_safe_design_raises():
    df = pd.DataFrame([
        {"material": "x", "section": "x", "dims": {}, "area": 1.0, "I": 1.0,
         "weight": 1.0, "cost": 1.0, "stress": 100.0, "deflection": 1.0,
         "fos": 0.5, "safe": False},
        {"material": "y", "section": "y", "dims": {}, "area": 2.0, "I": 2.0,
         "weight": 2.0, "cost": 0.5, "stress": 200.0, "deflection": 2.0,
         "fos": 0.8, "safe": False},
    ])

    with pytest.raises(ValueError):
        optimizer.recommend(df, "balanced")
