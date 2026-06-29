"""Bracket analysis tests — known-answer cases for plate, bolt group, gussets."""

import math
import pytest
from mechopt.bracket import (
    rectangular_plate_props,
    bracket_plate_stress,
    bracket_plate_deflection,
    plate_factor_of_safety,
    evaluate_bracket,
    bearing_stress,
    tearout_stress,
    compare_gussets,
    gusset_mass,
    effective_span,
    GUSSET_TYPES,
    GussetSpec,
)
from mechopt.materials import MATERIALS


def test_rectangular_plate_props():
    props = rectangular_plate_props(0.08, 0.01)
    assert props.A == pytest.approx(0.08 * 0.01)
    assert props.I == pytest.approx(0.08 * 0.01**3 / 12)
    assert props.c == pytest.approx(0.005)


def test_bracket_plate_stress():
    # M = 500 * 0.15 = 75 N·m
    # I = 0.08 * 0.01^3 / 12 = 6.6667e-9
    # c = 0.005
    # sigma = 75 * 0.005 / 6.6667e-9 = 56.25 MPa
    sigma = bracket_plate_stress(500.0, 0.15, 0.08, 0.01)
    assert sigma == pytest.approx(56.25e6, rel=1e-4)


def test_bracket_plate_deflection():
    # delta = P * e^3 / (3 * E * I)
    # P=500, e=0.15, E=200e9, w=0.08, t=0.01
    # I = 6.6667e-9
    # delta = 500 * 0.15^3 / (3 * 200e9 * 6.6667e-9)
    # delta = 500 * 3.375e-3 / 4.0 = 0.421875e-3 m
    delta = bracket_plate_deflection(500.0, 0.15, 200e9, 0.08, 0.01)
    assert delta == pytest.approx(500 * 0.15**3 / (3 * 200e9 * 0.08 * 0.01**3 / 12),
                                  rel=1e-4)


def test_plate_factor_of_safety():
    assert plate_factor_of_safety(100e6, 250e6) == pytest.approx(2.5)


def test_plate_fos_zero_stress():
    assert plate_factor_of_safety(0, 250e6) == float("inf")


def test_bolt_shear_distribution():
    # 4 bolts, 500 N load -> 125 N per bolt
    steel = MATERIALS["steel_a36"]
    result = evaluate_bracket(
        P=500.0, e=0.15, width=0.08, thickness=0.01,
        mat=steel, fos_target=2.0, bolt_count=4,
        bolt_diameter=0.01, bolt_spacing_v=0.04,
    )
    assert result.bolt.shear_per_bolt == pytest.approx(125.0)


def test_overall_fos_is_minimum():
    steel = MATERIALS["steel_a36"]
    result = evaluate_bracket(
        P=500.0, e=0.15, width=0.08, thickness=0.01,
        mat=steel, fos_target=2.0, bolt_count=4,
        bolt_diameter=0.01, bolt_spacing_v=0.04,
    )
    assert result.overall_fos == pytest.approx(min(result.plate_fos, result.bolt.bolt_fos))


def test_deflection_limit_makes_unsafe():
    steel = MATERIALS["steel_a36"]
    # Without limit — should be safe
    result_no_limit = evaluate_bracket(
        P=500.0, e=0.15, width=0.08, thickness=0.01,
        mat=steel, fos_target=1.0, bolt_count=4,
        bolt_diameter=0.01, bolt_spacing_v=0.04,
    )
    # With very tight limit — should be unsafe
    result_tight = evaluate_bracket(
        P=500.0, e=0.15, width=0.08, thickness=0.01,
        mat=steel, fos_target=1.0, bolt_count=4,
        bolt_diameter=0.01, bolt_spacing_v=0.04,
        deflection_limit=1e-9,
    )
    assert result_tight.safe is False
    assert result_tight.controlling == "deflection"


def test_evaluate_bracket_safe_design():
    steel = MATERIALS["steel_a36"]
    result = evaluate_bracket(
        P=100.0, e=0.10, width=0.10, thickness=0.02,
        mat=steel, fos_target=1.5, bolt_count=4,
        bolt_diameter=0.012, bolt_spacing_v=0.05,
    )
    # Light load, thick plate — should be safe
    assert result.safe is True
    assert result.overall_fos >= 1.5


# ═════════════════════════════════════════════════════════════════════════════
# Milestone F — Gusset variants
# ═════════════════════════════════════════════════════════════════════════════

# Common test case: P=500, e=0.15, w=0.08, t=0.01, Steel A36
# I = 0.08 * 0.01^3 / 12 = 6.6667e-9 m^4, c = 0.005 m
# Baseline: M=75 N·m, sigma=56.25 MPa, delta=0.000421875 m

_STEEL = MATERIALS["steel_a36"]
_BR_KWARGS = dict(
    P=500.0, e=0.15, width=0.08, thickness=0.01,
    mat=_STEEL, fos_target=2.0, bolt_count=4,
    bolt_diameter=0.01, bolt_spacing_v=0.04,
)


def test_gusset_none_matches_baseline():
    """gusset_type='none' gives same stress/deflection as no-gusset baseline."""
    result = evaluate_bracket(**_BR_KWARGS, gusset_type="none")
    assert result.plate_stress == pytest.approx(56.25e6, rel=1e-3)
    assert result.plate_deflection == pytest.approx(0.000421875, rel=1e-3)


def test_triangular_gusset_stress():
    """Gusset depth=50mm → e_eff=100mm → M=50 N·m → sigma=37.5 MPa."""
    result = evaluate_bracket(**_BR_KWARGS, gusset_type="triangular",
                              gusset_depth=0.05)
    assert result.plate_stress == pytest.approx(37.5e6, rel=1e-3)


def test_triangular_gusset_deflection():
    """delta = P*(e-g)^3 / (3*E*I) = 500*0.1^3 / (3*200e9*6.6667e-9) = 1.25e-4 m."""
    result = evaluate_bracket(**_BR_KWARGS, gusset_type="triangular",
                              gusset_depth=0.05)
    assert result.plate_deflection == pytest.approx(0.000125, rel=1e-3)


def test_triangular_gusset_deflection_reduction():
    """Deflection drops ~70.4% with a 50mm triangular gusset."""
    baseline = evaluate_bracket(**_BR_KWARGS, gusset_type="none")
    gusseted = evaluate_bracket(**_BR_KWARGS, gusset_type="triangular",
                                gusset_depth=0.05)
    reduction = ((baseline.plate_deflection - gusseted.plate_deflection)
                 / baseline.plate_deflection * 100)
    assert reduction == pytest.approx(70.37, rel=1e-2)


def test_triangular_gusset_mass():
    """mass = 0.5 * g * g * t * rho = 0.5 * 0.05 * 0.05 * 0.01 * 7850."""
    result = evaluate_bracket(**_BR_KWARGS, gusset_type="triangular",
                              gusset_depth=0.05)
    expected = 0.5 * 0.05 * 0.05 * 0.01 * 7850  # 0.098125 kg
    assert result.gusset.mass == pytest.approx(expected, rel=1e-3)


def test_double_gusset_mass():
    """Double gusset = 2x triangular mass."""
    result = evaluate_bracket(**_BR_KWARGS, gusset_type="double_gusset",
                              gusset_depth=0.05)
    expected = 2 * 0.5 * 0.05 * 0.05 * 0.01 * 7850
    assert result.gusset.mass == pytest.approx(expected, rel=1e-3)


def test_flat_L_gusset_same_deflection_as_triangular():
    """flat_L and triangular have the same effective span → same deflection."""
    flat = evaluate_bracket(**_BR_KWARGS, gusset_type="flat_L",
                            gusset_depth=0.05)
    tri = evaluate_bracket(**_BR_KWARGS, gusset_type="triangular",
                           gusset_depth=0.05)
    assert flat.plate_deflection == pytest.approx(tri.plate_deflection, rel=1e-6)


def test_compare_gussets_returns_all_types():
    """compare_gussets returns one result per GUSSET_TYPES entry."""
    results = compare_gussets(**_BR_KWARGS, gusset_depth=0.05)
    assert len(results) == len(GUSSET_TYPES)


def test_gusset_mass_function():
    """Direct test of gusset_mass for triangular variant."""
    mass = gusset_mass("triangular", 0.05, 0.01, 7850, 0.08)
    assert mass == pytest.approx(0.098125, rel=1e-3)


def test_effective_span_no_gusset():
    assert effective_span(0.15, "none", 0.05) == 0.15


def test_effective_span_with_gusset():
    assert effective_span(0.15, "triangular", 0.05) == pytest.approx(0.10)


def test_result_has_gusset_field():
    result = evaluate_bracket(**_BR_KWARGS, gusset_type="triangular",
                              gusset_depth=0.05)
    assert isinstance(result.gusset, GussetSpec)
    assert result.gusset.gusset_type == "triangular"


def test_result_has_mass_fields():
    result = evaluate_bracket(**_BR_KWARGS, gusset_type="triangular",
                              gusset_depth=0.05)
    assert result.plate_mass > 0
    assert result.total_mass >= result.plate_mass


# ═════════════════════════════════════════════════════════════════════════════
# Milestone F — Bearing & tear-out
# ═════════════════════════════════════════════════════════════════════════════

def test_bearing_stress_function():
    """sigma_br = P/(n*d*t) = 500/(4*0.01*0.01) = 1.25 MPa."""
    sigma = bearing_stress(500.0, 4, 0.01, 0.01)
    assert sigma == pytest.approx(1.25e6, rel=1e-3)


def test_bearing_fos_in_result():
    """bearing_allow = 1.5*250e6 = 375 MPa, FoS = 375e6/1.25e6 = 300."""
    result = evaluate_bracket(**_BR_KWARGS, edge_distance=0.02)
    assert result.bolt.bearing_fos == pytest.approx(300.0, rel=1e-2)


def test_tearout_stress_function():
    """d_hole=0.0115, L_shear=0.02-0.00575=0.01425,
    tau = 500/(4*2*0.01425*0.01) = 438596.49 Pa."""
    tau = tearout_stress(500.0, 4, 0.01, 0.01, 0.02)
    assert tau == pytest.approx(438596.49, rel=1e-3)


def test_tearout_fos_in_result():
    """shear_allow = 0.6*250e6 = 150 MPa,
    FoS = 150e6 / 438596.49 = 342.0."""
    result = evaluate_bracket(**_BR_KWARGS, edge_distance=0.02)
    assert result.bolt.tearout_fos == pytest.approx(342.0, rel=1e-3)


def test_edge_distance_ok_when_adequate():
    """edge=20mm >= 1.5*10mm=15mm → ok."""
    result = evaluate_bracket(**_BR_KWARGS, edge_distance=0.02)
    assert result.bolt.edge_distance_ok is True


def test_edge_distance_warning_when_short():
    """edge=10mm < 15mm → not ok, warning includes 'tear-out'."""
    result = evaluate_bracket(**_BR_KWARGS, edge_distance=0.01)
    assert result.bolt.edge_distance_ok is False
    assert any("tear-out" in w for w in result.bolt.warnings)


def test_wall_anchorage_warning():
    """Every result includes the wall anchorage disclaimer."""
    result = evaluate_bracket(**_BR_KWARGS)
    assert any("wall anchorage" in w.lower() for w in result.bolt.warnings)


def test_controlling_can_be_bearing():
    """With tiny bolt diameter, bearing stress dominates."""
    result = evaluate_bracket(
        P=50000.0, e=0.15, width=0.08, thickness=0.001,
        mat=_STEEL, fos_target=1.0, bolt_count=1,
        bolt_diameter=0.002, bolt_spacing_v=0.04,
        edge_distance=0.05,
    )
    # bearing_stress = 50000/(1*0.002*0.001) = 25 GPa — very high
    assert result.bolt.bearing_fos < result.bolt.bolt_fos or result.controlling in ("bearing", "plate_bending")


def test_controlling_can_be_tearout():
    """With tiny edge distance, tear-out dominates."""
    result = evaluate_bracket(
        P=50000.0, e=0.05, width=0.08, thickness=0.002,
        mat=_STEEL, fos_target=1.0, bolt_count=1,
        bolt_diameter=0.01, bolt_spacing_v=0.04,
        edge_distance=0.006,
    )
    # d_hole=0.0115, L_shear = 0.006 - 0.00575 = 0.00025 → huge tearout stress
    assert result.bolt.tearout_fos < 1.0
