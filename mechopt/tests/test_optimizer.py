"""Optimizer / recommendation tests (behavioral, not exact-value)."""

import pytest
from mechopt import optimizer

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


def test_no_safe_design_raises():
    # Absurd load with a tiny FoS-impossible target -> nothing safe.
    df = optimizer.evaluate_candidates(
        load=1e7, length=5.0, load_case="simply_center", fos_target=10.0
    )
    if not df["safe"].any():
        with pytest.raises(ValueError):
            optimizer.recommend(df, "balanced")
