"""Oracle-first tests for stock.py — Milestone E (Manufacturing realism).

All numeric targets are hand-derived from the governing equations.
Never edit a target to make a test pass; fix the code instead.

Catalog constants used throughout:
    STOCK_DIMS_MM = [10, 12, 15, 16, 20, 25, 30, 35, 40, 45, 50, 60, 70, 80, 90, 100]
    WALL_THICKNESSES_MM = [1, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 10]
    BOLT_SIZES = ["M3", "M4", "M5", "M6", "M8", "M10"]

nearest_buyable oracle (Steel A36 rectangle, P=500 N, L=1.0 m, cantilever_end):

  On-stock design (d=30 mm, which is IN STOCK_DIMS_MM):
    A = 0.030^2           = 9.000e-4  m^2
    I = 0.030^4 / 12      = 6.750e-8  m^4
    c = 0.030 / 2         = 0.015     m
    M = P * L             = 500       N*m
    sigma = M*c/I         = 500*0.015/6.75e-8  = 111,111,111 Pa ~ 111.111 MPa
    delta = P*L^3/(3EI)   = 500/(3*200e9*6.75e-8) = 0.012346 m
    fos   = 250e6/111.111e6 = 2.25
    weight = 9e-4*1.0*7850  = 7.065  kg
    cost   = 7.065*1.0      = 7.065  USD
    snap -> 30 mm (no change) => mass_penalty_pct = 0.0, stiffness_change_pct = 0.0

  Non-stock design (d=22 mm, snaps to 20 mm):
    I_orig = 0.022^4 / 12  = 1.95213e-8  m^4
    I_snap = 0.020^4 / 12  = 1.33333e-8  m^4
    w_orig = 0.022^2*7850   = 3.7994  kg
    w_snap = 0.020^2*7850   = 3.14    kg
    mass_penalty_pct   = (3.14 - 3.7994)/3.7994 * 100  = -17.354%
    stiffness_change_pct = (1.33333e-8 - 1.95213e-8)/1.95213e-8 * 100 = -31.699%
"""

import numpy as np
import pytest

from mechopt import optimizer
from mechopt.stock import (
    BOLT_SIZES,
    STOCK_DIMS_MM,
    WALL_THICKNESSES_MM,
    StockComparison,
    _snap,
    nearest_buyable,
    stock_dims_mm,
)


# ── Catalog constants ────────────────────────────────────────────────────────

class TestCatalogConstants:
    def test_stock_dims_mm_is_list(self):
        assert isinstance(STOCK_DIMS_MM, list)

    def test_stock_dims_mm_length(self):
        assert len(STOCK_DIMS_MM) == 16

    def test_stock_dims_mm_first(self):
        assert STOCK_DIMS_MM[0] == 10

    def test_stock_dims_mm_last(self):
        assert STOCK_DIMS_MM[-1] == 100

    def test_wall_thicknesses_mm_is_list(self):
        assert isinstance(WALL_THICKNESSES_MM, list)

    def test_wall_thicknesses_mm_nonempty(self):
        assert len(WALL_THICKNESSES_MM) > 0

    def test_bolt_sizes_is_list(self):
        assert isinstance(BOLT_SIZES, list)

    def test_bolt_sizes_contains_m6(self):
        assert "M6" in BOLT_SIZES

    def test_bolt_sizes_contains_m3_through_m10(self):
        for size in ["M3", "M4", "M5", "M6", "M8", "M10"]:
            assert size in BOLT_SIZES


# ── stock_dims_mm() ───────────────────────────────────────────────────────────

class TestStockDimsMm:
    def test_returns_numpy_array(self):
        result = stock_dims_mm()
        assert isinstance(result, np.ndarray)

    def test_has_16_elements(self):
        result = stock_dims_mm()
        assert len(result) == 16

    def test_first_element_is_10(self):
        result = stock_dims_mm()
        assert result[0] == pytest.approx(10.0)

    def test_last_element_is_100(self):
        result = stock_dims_mm()
        assert result[-1] == pytest.approx(100.0)

    def test_matches_stock_dims_mm_list(self):
        result = stock_dims_mm()
        assert list(result) == [float(v) for v in STOCK_DIMS_MM]


# ── _snap ─────────────────────────────────────────────────────────────────────

class TestSnap:
    """Tests for _snap(value, catalog) -> nearest catalog value."""

    def test_snap_nearest_below(self):
        # 22 is closer to 20 (distance 2) than to 30 (distance 8)
        assert _snap(22, [10, 20, 30]) == 20

    def test_snap_equidistant(self):
        # 25 is exactly halfway between 20 and 30; either is acceptable
        result = _snap(25, [10, 20, 30])
        assert result in [20, 30]

    def test_snap_below_range_clamps_to_min(self):
        # 5 is below the smallest catalog value; clamps to 10
        assert _snap(5, [10, 20, 30]) == 10

    def test_snap_above_range_clamps_to_max(self):
        # 100 is above all catalog values; clamps to 30
        assert _snap(100, [10, 20, 30]) == 30

    def test_snap_exact_match(self):
        # Exact hit should return that value
        assert _snap(20, [10, 20, 30]) == 20

    def test_snap_single_element_catalog(self):
        # Only one option available
        assert _snap(999, [42]) == 42

    def test_snap_nearest_above(self):
        # 28 is closer to 30 (distance 2) than to 20 (distance 8)
        assert _snap(28, [10, 20, 30]) == 30

    def test_snap_on_stock_30mm(self):
        # 30 is in STOCK_DIMS_MM — must return 30 exactly
        assert _snap(30, STOCK_DIMS_MM) == 30

    def test_snap_22mm_to_stock(self):
        # 22 is between 20 and 25; 20 is closer (distance 2 vs 3)
        assert _snap(22, STOCK_DIMS_MM) == 20


# ── StockComparison fields ────────────────────────────────────────────────────

class TestStockComparisonFields:
    """Structural checks: StockComparison must carry all expected attributes."""

    @pytest.fixture(scope="class")
    def comparison_30mm(self):
        """On-stock design: Steel A36, rectangle 30x30 mm, P=500N, L=1.0m."""
        theoretical = {
            "material": "Steel A36",
            "section": "rectangle",
            "dims": "30x30 mm",
            # Hand-derived from equations above
            "area": 9.0e-4,           # 0.030^2
            "I": 6.75e-8,             # 0.030^4 / 12
            "weight": 7.065,          # 9e-4 * 1.0 * 7850
            "cost": 7.065,            # weight * 1.0 USD/kg
            "stress": 111_111_111.11, # M*c/I = 500*0.015/6.75e-8
            "deflection": 0.012346,   # P*L^3/(3*E*I)
            "fos": 2.25,              # 250e6/111.111e6
            "safe": True,
        }
        return nearest_buyable(
            theoretical,
            load=500.0,
            length=1.0,
            load_case="cantilever_end",
            fos_target=2.0,
        )

    def test_has_original_field(self, comparison_30mm):
        assert hasattr(comparison_30mm, "original")

    def test_has_snapped_field(self, comparison_30mm):
        assert hasattr(comparison_30mm, "snapped")

    def test_has_snapped_dims_mm_field(self, comparison_30mm):
        assert hasattr(comparison_30mm, "snapped_dims_mm")

    def test_has_mass_penalty_pct(self, comparison_30mm):
        assert hasattr(comparison_30mm, "mass_penalty_pct")

    def test_has_stiffness_change_pct(self, comparison_30mm):
        assert hasattr(comparison_30mm, "stiffness_change_pct")

    def test_has_fos_change(self, comparison_30mm):
        assert hasattr(comparison_30mm, "fos_change")

    def test_has_summary(self, comparison_30mm):
        assert hasattr(comparison_30mm, "summary")

    def test_summary_is_string(self, comparison_30mm):
        assert isinstance(comparison_30mm.summary, str)

    def test_summary_contains_stock_snap_label(self, comparison_30mm):
        assert "Stock snap:" in comparison_30mm.summary


# ── nearest_buyable — on-stock oracle (d=30mm, no snap change) ───────────────

class TestNearestBuyableOnStock:
    """
    Theoretical design: Steel A36, rectangle 30x30 mm.
    30 mm IS in STOCK_DIMS_MM, so snap is a no-op.
    Mass and stiffness changes must be zero; re-computed values must match
    the hand-derived equations.

    Hand derivation (P=500N, L=1.0m, cantilever_end, Steel A36 E=200e9, rho=7850, sigma_y=250e6):
        A     = 0.030^2                         = 9.000e-4 m^2
        I     = 0.030^4 / 12                    = 6.750e-8 m^4
        c     = 0.030 / 2                       = 0.015 m
        M     = P * L                           = 500.0 N*m
        sigma = M * c / I  = 500*0.015/6.75e-8 = 111,111,111.11 Pa
        delta = P*L^3/(3EI) = 500/(3*200e9*6.75e-8) = 0.012346 m
        fos   = 250e6 / 111,111,111             = 2.25
        weight = A * L * rho = 9e-4 * 1.0 * 7850 = 7.065 kg
        cost   = weight * 1.0                   = 7.065 USD
    """

    @pytest.fixture(scope="class")
    def sc(self):
        theoretical = {
            "material": "Steel A36",
            "section": "rectangle",
            "dims": "30x30 mm",
            "area": 9.0e-4,
            "I": 6.75e-8,
            "weight": 7.065,
            "cost": 7.065,
            "stress": 500.0 * 0.015 / 6.75e-8,
            "deflection": 500.0 / (3 * 200e9 * 6.75e-8),
            "fos": 250e6 / (500.0 * 0.015 / 6.75e-8),
            "safe": True,
        }
        return nearest_buyable(
            theoretical,
            load=500.0,
            length=1.0,
            load_case="cantilever_end",
            fos_target=2.0,
        )

    def test_snapped_dim_is_30mm(self, sc):
        assert sc.snapped_dims_mm["d_mm"] == pytest.approx(30.0)

    def test_mass_penalty_is_zero(self, sc):
        # 30 mm is in catalog; no size change, so mass change is 0.0%
        assert sc.mass_penalty_pct == pytest.approx(0.0, abs=1e-6)

    def test_stiffness_change_is_zero(self, sc):
        # Same I; no change
        assert sc.stiffness_change_pct == pytest.approx(0.0, abs=1e-6)

    def test_fos_change_is_zero(self, sc):
        # Same geometry => same FoS
        assert sc.fos_change == pytest.approx(0.0, abs=1e-6)

    def test_snapped_weight(self, sc):
        # weight = 9e-4 * 1.0 * 7850 = 7.065 kg
        assert sc.snapped["weight"] == pytest.approx(7.065, rel=1e-3)

    def test_snapped_cost(self, sc):
        # cost = 7.065 * 1.0 = 7.065 USD
        assert sc.snapped["cost"] == pytest.approx(7.065, rel=1e-3)

    def test_snapped_fos(self, sc):
        # fos = 250e6 / (500*0.015/6.75e-8) = 2.25
        assert sc.snapped["fos"] == pytest.approx(2.25, rel=1e-3)

    def test_snapped_stress(self, sc):
        # sigma = 500*0.015/6.75e-8 = 111,111,111 Pa
        assert sc.snapped["stress"] == pytest.approx(111_111_111.11, rel=1e-3)

    def test_snapped_moment_of_inertia(self, sc):
        # I = 0.030^4 / 12 = 6.75e-8 m^4
        assert sc.snapped["I"] == pytest.approx(6.75e-8, rel=1e-3)

    def test_snapped_is_safe(self, sc):
        # fos=2.25 >= fos_target=2.0 => safe
        assert sc.snapped["safe"] is True


# ── nearest_buyable — non-stock oracle (d=22mm snaps to 20mm) ────────────────

class TestNearestBuyableNonStock:
    """
    Theoretical design: Steel A36, rectangle 22x22 mm (NOT in STOCK_DIMS_MM).
    Nearest stock size = 20 mm (|22-20|=2 < |22-25|=3).

    Hand derivation (original at d=22mm):
        I_orig = 0.022^4 / 12 = (2.2e-2)^4 / 12
               = (2.2)^4 * 1e-8 / 12
               = 23.4256e-8 / 12
               = 1.952133e-8  m^4
        w_orig = 0.022^2 * 1.0 * 7850 = 4.84e-4 * 7850 = 3.7994 kg

    Snapped at d=20mm:
        I_snap = 0.020^4 / 12 = 16e-8 / 12 = 1.333333e-8  m^4
        w_snap = 0.020^2 * 1.0 * 7850 = 4.00e-4 * 7850 = 3.14 kg

    mass_penalty_pct   = (3.14 - 3.7994) / 3.7994 * 100 = -17.354%
    stiffness_change_pct = (1.333333e-8 - 1.952133e-8) / 1.952133e-8 * 100
                         = -0.618800e-8 / 1.952133e-8 * 100
                         = -31.699%
    """

    # Pre-computed oracle constants (hand-derived)
    I_ORIG = 0.022 ** 4 / 12        # 1.952133e-8 m^4
    I_SNAP = 0.020 ** 4 / 12        # 1.333333e-8 m^4
    W_ORIG = 0.022 ** 2 * 7850      # 3.7994 kg
    W_SNAP = 0.020 ** 2 * 7850      # 3.14 kg
    MASS_PCT = (W_SNAP - W_ORIG) / W_ORIG * 100      # -17.354%
    STIFF_PCT = (I_SNAP - I_ORIG) / I_ORIG * 100     # -31.699%

    @pytest.fixture(scope="class")
    def sc(self):
        # Build a synthetic theoretical row as if the optimizer produced it
        d_orig = 0.022
        I_orig = d_orig ** 4 / 12
        c_orig = d_orig / 2
        M = 500.0 * 1.0
        sigma_orig = M * c_orig / I_orig
        delta_orig = 500.0 / (3 * 200e9 * I_orig)
        fos_orig = 250e6 / sigma_orig
        weight_orig = d_orig ** 2 * 7850
        cost_orig = weight_orig * 1.0

        theoretical = {
            "material": "Steel A36",
            "section": "rectangle",
            "dims": "22x22 mm",   # non-stock string; _parse_dims reads the numbers
            "area": d_orig ** 2,
            "I": I_orig,
            "weight": weight_orig,
            "cost": cost_orig,
            "stress": sigma_orig,
            "deflection": delta_orig,
            "fos": fos_orig,
            "safe": False,  # fos < 2.0 at 22mm
        }
        return nearest_buyable(
            theoretical,
            load=500.0,
            length=1.0,
            load_case="cantilever_end",
            fos_target=2.0,
        )

    def test_snapped_dim_is_20mm(self, sc):
        # 22 -> nearest stock = 20 (closer than 25)
        assert sc.snapped_dims_mm["d_mm"] == pytest.approx(20.0)

    def test_mass_penalty_pct(self, sc):
        # (3.14 - 3.7994) / 3.7994 * 100 = -17.354%
        expected = self.MASS_PCT
        assert sc.mass_penalty_pct == pytest.approx(expected, rel=1e-3)

    def test_stiffness_change_pct(self, sc):
        # (I_snap - I_orig) / I_orig * 100 = -31.699%
        expected = self.STIFF_PCT
        assert sc.stiffness_change_pct == pytest.approx(expected, rel=1e-3)

    def test_mass_penalty_is_negative(self, sc):
        # Snapping down from 22mm to 20mm reduces mass
        assert sc.mass_penalty_pct < 0.0

    def test_stiffness_change_is_negative(self, sc):
        # Smaller section -> lower I
        assert sc.stiffness_change_pct < 0.0

    def test_fos_change_is_negative(self, sc):
        # Smaller section -> higher stress -> lower FoS
        assert sc.fos_change < 0.0

    def test_snapped_weight(self, sc):
        # w_snap = 0.020^2 * 7850 = 3.14 kg
        assert sc.snapped["weight"] == pytest.approx(self.W_SNAP, rel=1e-3)

    def test_snapped_I(self, sc):
        # I_snap = 0.020^4 / 12 = 1.333333e-8 m^4
        assert sc.snapped["I"] == pytest.approx(self.I_SNAP, rel=1e-3)

    def test_summary_contains_stock_snap(self, sc):
        assert "Stock snap:" in sc.summary

    def test_summary_mentions_20mm(self, sc):
        assert "20" in sc.summary


# ── stock_mode optimizer integration ─────────────────────────────────────────

class TestStockModeOptimizer:
    """evaluate_candidates(stock_mode=True) must use STOCK_DIMS_MM grid."""

    @pytest.fixture(scope="class")
    def df_stock(self):
        return optimizer.evaluate_candidates(
            load=500.0,
            length=1.0,
            load_case="cantilever_end",
            fos_target=2.0,
            stock_mode=True,
        )

    @pytest.fixture(scope="class")
    def df_sweep(self):
        return optimizer.evaluate_candidates(
            load=500.0,
            length=1.0,
            load_case="cantilever_end",
            fos_target=2.0,
            stock_mode=False,
        )

    def test_stock_mode_returns_nonempty_dataframe(self, df_stock):
        assert len(df_stock) > 0

    def test_stock_mode_has_required_columns(self, df_stock):
        required = {"material", "section", "dims", "area", "I", "weight",
                    "cost", "stress", "deflection", "fos", "safe"}
        assert required.issubset(set(df_stock.columns))

    def test_stock_mode_dims_are_from_catalog(self, df_stock):
        """Every dims string must embed only stock dimension values.

        The optimizer formats rectangle dims as 'NxN mm', so we extract the
        leading integer and check it is in STOCK_DIMS_MM.
        """
        import re
        rect_rows = df_stock[df_stock["section"] == "rectangle"]
        for dims_str in rect_rows["dims"]:
            nums = [float(x) for x in re.findall(r"[\d.]+", dims_str)]
            if nums:
                assert nums[0] in STOCK_DIMS_MM, (
                    f"Dim {nums[0]} mm from '{dims_str}' is not in STOCK_DIMS_MM"
                )

    def test_stock_mode_has_safe_designs(self, df_stock):
        # With P=500N, L=1m, at least some steel or aluminum designs are safe
        assert df_stock["safe"].any()

    def test_sweep_mode_dims_not_all_in_catalog(self, df_sweep):
        """The classic arange(10,110,10) grid is already all multiples of 10.
        Since STOCK_DIMS_MM contains all multiples of 10 in [10,100] (10,20,...,100),
        we verify that stock_mode=False uses the arange grid specifically by
        checking the count of distinct rectangle dim values.

        arange grid: 10,20,30,40,50,60,70,80,90,100 -> 10 values
        stock grid:  10,12,15,16,20,25,30,35,40,45,50,60,70,80,90,100 -> 16 values
        """
        import re
        rect_rows = df_sweep[df_sweep["section"] == "rectangle"]
        dims_seen = set()
        for dims_str in rect_rows["dims"]:
            nums = [float(x) for x in re.findall(r"[\d.]+", dims_str)]
            if nums:
                dims_seen.add(nums[0])
        # arange(10,110,10) gives exactly 10 distinct dimension values
        assert len(dims_seen) == 10

    def test_stock_mode_more_dims_than_sweep(self, df_stock, df_sweep):
        """stock_mode=True uses 16 catalog sizes vs 10 for the arange grid."""
        import re

        def count_rect_dims(df):
            dims_seen = set()
            for dims_str in df[df["section"] == "rectangle"]["dims"]:
                nums = [float(x) for x in re.findall(r"[\d.]+", dims_str)]
                if nums:
                    dims_seen.add(nums[0])
            return len(dims_seen)

        assert count_rect_dims(df_stock) > count_rect_dims(df_sweep)

    def test_stock_mode_row_count_differs_from_sweep(self, df_stock, df_sweep):
        # Different grid -> different total row count
        assert len(df_stock) != len(df_sweep)
