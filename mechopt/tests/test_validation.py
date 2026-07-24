"""Cross-validation: the analytical model must agree with an independent FE solver.

This is a PROPERTY test, not a known-answer test: it asserts that two independent
methods (closed-form beam.py vs. the direct-stiffness FE solver in
validation/fea_beam.py) produce the same deflection and moment. No numeric target
is hardcoded here, so it stays valid even if the inputs change.
"""
import pytest

from modulus import sections, beam
from modulus.materials import MATERIALS
from validation.fea_beam import solve as fe_solve

CASES = [
    ("steel_a36",     sections.rectangle(0.030, 0.030),        300.0, 0.8, "cantilever_end"),
    ("aluminum_6061", sections.circle(0.030),                  800.0, 1.2, "simply_center"),
    ("steel_a36",     sections.square_tube(0.040, 0.004),      600.0, 1.0, "cantilever_end"),
    ("aluminum_6061", sections.i_beam(0.050, 0.100, 0.008, 0.006), 1200.0, 1.5, "simply_center"),
]


@pytest.mark.parametrize("mkey,props,P,L,lc", CASES)
def test_fe_matches_analytical_deflection(mkey, props, P, L, lc):
    mat = MATERIALS[mkey]
    d_anl = beam.max_deflection(P, L, mat.E, props, lc)
    d_fe, _ = fe_solve(P, L, mat.E, props.I, lc, ne=400)
    assert d_fe == pytest.approx(d_anl, rel=1e-4)


@pytest.mark.parametrize("mkey,props,P,L,lc", CASES)
def test_fe_matches_analytical_moment(mkey, props, P, L, lc):
    mat = MATERIALS[mkey]
    M_anl = beam.max_moment(P, L, lc)
    _, M_fe = fe_solve(P, L, mat.E, props.I, lc, ne=400)
    assert M_fe == pytest.approx(M_anl, rel=1e-3)
