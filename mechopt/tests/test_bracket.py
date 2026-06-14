"""Bracket analysis tests — known-answer cases for plate and bolt group."""

import math
import pytest
from mechopt.bracket import (
    rectangular_plate_props,
    bracket_plate_stress,
    bracket_plate_deflection,
    plate_factor_of_safety,
    evaluate_bracket,
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
