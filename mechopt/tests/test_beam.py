"""Beam-mechanics tests against hand-verified known-answer cases.

See SPEC.md "Known-answer reference cases". The targets here were computed
independently and should be checked by hand before trusting any implementation.
"""

import pytest
from modulus import sections, beam
from modulus.materials import MATERIALS


def test_case_A_steel_square_cantilever():
    """Steel A36, 30x30 mm square, L=0.8 m, P=300 N, cantilever end load."""
    steel = MATERIALS["steel_a36"]
    props = sections.rectangle(0.03, 0.03)
    P, L = 300.0, 0.8

    M = beam.max_moment(P, L, "cantilever_end")
    sigma = beam.max_stress(M, props)
    delta = beam.max_deflection(P, L, steel.E, props, "cantilever_end")
    fos = beam.factor_of_safety(sigma, steel.sigma_y)

    assert M == pytest.approx(240.0)
    assert sigma == pytest.approx(53.3333e6, rel=1e-4)
    assert delta == pytest.approx(3.7926e-3, rel=1e-3)
    assert fos == pytest.approx(4.6875, rel=1e-4)


def test_case_B_aluminum_circle_simply_supported():
    """Aluminum 6061, d=30 mm circle, L=1.2 m, P=800 N, simply supported center."""
    al = MATERIALS["aluminum_6061"]
    props = sections.circle(0.03)
    P, L = 800.0, 1.2

    M = beam.max_moment(P, L, "simply_center")
    sigma = beam.max_stress(M, props)
    delta = beam.max_deflection(P, L, al.E, props, "simply_center")
    fos = beam.factor_of_safety(sigma, al.sigma_y)

    assert M == pytest.approx(240.0)
    assert sigma == pytest.approx(90.5415e6, rel=1e-4)
    assert delta == pytest.approx(10.4976e-3, rel=1e-3)
    assert fos == pytest.approx(3.0373, rel=1e-4)


def test_factor_of_safety_basic():
    assert beam.factor_of_safety(100e6, 250e6) == pytest.approx(2.5)
