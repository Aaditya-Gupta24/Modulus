"""Oracle-first tests for the decision module (Milestone C).

These tests encode hand-derived oracle targets for ranking, Pareto-front
extraction, knee-point identification, infeasibility classification, and
winner explanation.  The module under test does NOT exist yet -- importing
it will fail until decision.py is implemented.  That is intentional
(red-green-refactor).

Oracle derivations are documented inline next to each assertion.
"""

import pytest
import pandas as pd
from modulus.failure_modes import SafetyCase, CheckResult, Status
from modulus.decision import (
    rank_candidates,
    pareto_front,
    knee_point,
    classify_infeasible,
    explain_winner,
)


# ---------------------------------------------------------------------------
# Helpers — build a deterministic 5-candidate DataFrame
# ---------------------------------------------------------------------------

def _sc(controlling, reasons=None):
    """Build a minimal SafetyCase for test candidates."""
    return SafetyCase(
        checks=[],
        overall_status=Status.FAIL if reasons else Status.PASS,
        controlling_check=controlling,
        failure_reasons=reasons or [],
    )


def _test_frame():
    """5 safe candidates with known weight/cost for Pareto analysis.

    Candidate  weight  cost   fos
    A          1.0     5.0    3.0
    B          2.0     2.0    4.0
    C          1.5     3.0    3.5
    D          3.0     4.0    5.0
    E          4.0     6.0    2.0
    """
    data = [
        {"material": "A", "section": "rect", "dims": "10x10",
         "weight": 1.0, "cost": 5.0, "fos": 3.0,
         "stress": 80e6, "deflection": 0.003, "safe": True,
         "area": 1e-4, "I": 1e-8,
         "safety_case": _sc("deflection")},
        {"material": "B", "section": "rect", "dims": "20x20",
         "weight": 2.0, "cost": 2.0, "fos": 4.0,
         "stress": 60e6, "deflection": 0.002, "safe": True,
         "area": 4e-4, "I": 1.3e-8,
         "safety_case": _sc("bending_stress")},
        {"material": "C", "section": "rect", "dims": "15x15",
         "weight": 1.5, "cost": 3.0, "fos": 3.5,
         "stress": 70e6, "deflection": 0.0025, "safe": True,
         "area": 2.25e-4, "I": 1.1e-8,
         "safety_case": _sc("deflection")},
        {"material": "D", "section": "rect", "dims": "30x30",
         "weight": 3.0, "cost": 4.0, "fos": 5.0,
         "stress": 50e6, "deflection": 0.001, "safe": True,
         "area": 9e-4, "I": 6.75e-8,
         "safety_case": _sc("bending_stress")},
        {"material": "E", "section": "rect", "dims": "40x40",
         "weight": 4.0, "cost": 6.0, "fos": 2.0,
         "stress": 100e6, "deflection": 0.005, "safe": True,
         "area": 16e-4, "I": 2.1e-7,
         "safety_case": _sc("bending_stress")},
    ]
    return pd.DataFrame(data)


def _test_frame_with_unsafe():
    """Extend _test_frame with two unsafe candidates F and G."""
    df = _test_frame()
    unsafe = pd.DataFrame([
        {"material": "F", "section": "rect", "dims": "5x5",
         "weight": 0.5, "cost": 1.0, "fos": 0.8,
         "stress": 200e6, "deflection": 0.010, "safe": False,
         "area": 2.5e-5, "I": 5e-10,
         "safety_case": _sc("deflection", ["deflection"])},
        {"material": "G", "section": "rect", "dims": "8x8",
         "weight": 0.8, "cost": 1.5, "fos": 0.5,
         "stress": 250e6, "deflection": 0.012, "safe": False,
         "area": 6.4e-5, "I": 3.4e-9,
         "safety_case": _sc("bending_stress",
                            ["bending_stress", "deflection"])},
    ])
    return pd.concat([df, unsafe], ignore_index=True)


def _all_unsafe_frame():
    """DataFrame where every candidate is unsafe."""
    data = [
        {"material": "X", "section": "rect", "dims": "5x5",
         "weight": 0.5, "cost": 1.0, "fos": 0.5,
         "stress": 300e6, "deflection": 0.020, "safe": False,
         "area": 2.5e-5, "I": 5e-10,
         "safety_case": _sc("deflection", ["deflection"])},
        {"material": "Y", "section": "rect", "dims": "6x6",
         "weight": 0.6, "cost": 1.2, "fos": 0.6,
         "stress": 280e6, "deflection": 0.018, "safe": False,
         "area": 3.6e-5, "I": 1.1e-9,
         "safety_case": _sc("bending_stress", ["bending_stress"])},
    ]
    return pd.DataFrame(data)


# ---------------------------------------------------------------------------
# 1. Pareto-front extraction
# ---------------------------------------------------------------------------

def test_pareto_front_known_set():
    """Pareto front of _test_frame is {A, B, C} (indices 0, 1, 2).

    Oracle derivation (minimize weight, minimize cost):
      A (1.0, 5.0) — not dominated: no candidate has weight<=1.0 AND cost<5.0
      B (2.0, 2.0) — not dominated: no candidate has weight<=2.0 AND cost<2.0
      C (1.5, 3.0) — not dominated: A has lower weight but higher cost;
                      B has lower cost but higher weight
    """
    df = _test_frame()
    front = pareto_front(df)

    assert len(front) == 3
    front_materials = set(front["material"].tolist())
    assert front_materials == {"A", "B", "C"}


# ---------------------------------------------------------------------------
# 2. Dominated candidates excluded
# ---------------------------------------------------------------------------

def test_dominated_excluded():
    """D and E must NOT appear in the Pareto front.

    D (3.0, 4.0): dominated by C (1.5 < 3.0 AND 3.0 < 4.0).
    E (4.0, 6.0): dominated by A (1.0 < 4.0 AND 5.0 < 6.0).
    """
    df = _test_frame()
    front = pareto_front(df)

    front_materials = set(front["material"].tolist())
    assert "D" not in front_materials
    assert "E" not in front_materials


# ---------------------------------------------------------------------------
# 3. Knee point
# ---------------------------------------------------------------------------

def test_knee_point_is_c():
    """Knee point on the Pareto front is candidate C (index 2).

    Oracle derivation in normalized [0,1] space:
      Ideal = (min_weight=1.0, min_cost=2.0)
      weight range = 2.0 - 1.0 = 1.0;  cost range = 5.0 - 2.0 = 3.0

      A_norm = (0.0, 1.0)  -> dist = 1.0
      B_norm = (1.0, 0.0)  -> dist = 1.0
      C_norm = (0.5, 0.333) -> dist = sqrt(0.25 + 0.111) = 0.601

    C is closest to ideal -> knee.
    """
    df = _test_frame()
    front = pareto_front(df)
    knee_idx = knee_point(front)

    # knee_point returns the original df index of the knee candidate
    assert df.loc[knee_idx, "material"] == "C"


# ---------------------------------------------------------------------------
# 4. Rank by lightest
# ---------------------------------------------------------------------------

def test_rank_lightest():
    """priority='lightest' sorts by ascending weight.

    Expected order: A(1.0)=1, C(1.5)=2, B(2.0)=3, D(3.0)=4, E(4.0)=5.
    """
    df = _test_frame()
    ranked = rank_candidates(df, priority="lightest")

    # Build a material->rank mapping for easy assertion
    rank_map = dict(zip(ranked["material"], ranked["rank"]))
    assert rank_map["A"] == 1
    assert rank_map["C"] == 2
    assert rank_map["B"] == 3
    assert rank_map["D"] == 4
    assert rank_map["E"] == 5


# ---------------------------------------------------------------------------
# 5. Rank by safest
# ---------------------------------------------------------------------------

def test_rank_safest():
    """priority='safest' sorts by descending FoS.

    Expected: D(fos=5.0)=1, B(fos=4.0)=2, C(fos=3.5)=3, A(fos=3.0)=4,
              E(fos=2.0)=5.
    """
    df = _test_frame()
    ranked = rank_candidates(df, priority="safest")

    rank_map = dict(zip(ranked["material"], ranked["rank"]))
    assert rank_map["D"] == 1
    assert rank_map["B"] == 2
    assert rank_map["C"] == 3
    assert rank_map["A"] == 4
    assert rank_map["E"] == 5


# ---------------------------------------------------------------------------
# 6. Classify infeasible
# ---------------------------------------------------------------------------

def test_classify_infeasible():
    """Safe rows -> 'feasible'; unsafe rows -> pipe-separated failure reasons.

    F has failure_reasons=['deflection']       -> 'failed_deflection'
    G has failure_reasons=['bending_stress',
                           'deflection']       -> 'failed_bending_stress|failed_deflection'
    All safe rows (A-E)                        -> 'feasible'
    """
    df = _test_frame_with_unsafe()
    result = classify_infeasible(df)

    # Same index as input
    assert len(result) == len(df)

    # Safe rows
    for i in range(5):
        assert result.iloc[i] == "feasible"

    # Unsafe rows
    assert result.iloc[5] == "failed_deflection"
    assert result.iloc[6] == "failed_bending_stress|failed_deflection"


# ---------------------------------------------------------------------------
# 7. Explain winner
# ---------------------------------------------------------------------------

def test_explain_winner():
    """explain_winner returns a non-empty string mentioning the controlling
    constraint for the given candidate row."""
    df = _test_frame()
    # Pick candidate A whose controlling check is 'deflection'
    row = df.iloc[0]
    explanation = explain_winner(row)

    assert isinstance(explanation, str)
    assert len(explanation) > 0
    assert "deflection" in explanation.lower()


# ---------------------------------------------------------------------------
# 8. Pareto front empty when no safe candidates
# ---------------------------------------------------------------------------

def test_pareto_front_empty_when_no_safe():
    """When every candidate is unsafe, pareto_front returns an empty
    DataFrame."""
    df = _all_unsafe_frame()
    front = pareto_front(df)

    assert isinstance(front, pd.DataFrame)
    assert len(front) == 0


# ---------------------------------------------------------------------------
# 9. Rank assigns None to unsafe candidates
# ---------------------------------------------------------------------------

def test_rank_unsafe_get_none():
    """Unsafe candidates should receive rank=None in ranked output."""
    df = _test_frame_with_unsafe()
    ranked = rank_candidates(df, priority="lightest")

    unsafe_rows = ranked[ranked["safe"] == False]  # noqa: E712
    for _, row in unsafe_rows.iterrows():
        assert pd.isna(row["rank"])
