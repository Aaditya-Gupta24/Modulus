"""Known-answer and property tests for Euler column buckling.

Targets are derived from P_cr = pi^2 E I / (K L)^2, not copied from code output.

Reference case: steel A36 (E = 200e9 Pa), solid 30x30 mm square
(I = 6.75e-8 m^4, A = 9e-4 m^2), L = 0.8 m.

    K = 1.0 : P_cr = pi^2 (200e9)(6.75e-8) / (1.0*0.8)^2 = 208186.9678 N
    K = 2.0 : P_cr = pi^2 (200e9)(6.75e-8) / (2.0*0.8)^2 =  52046.7420 N
    r       = sqrt(6.75e-8 / 9e-4) = 0.008660254 m
    lambda  = 1.0*0.8 / 0.008660254 = 92.3760 (K=1)
"""
import math

import pytest

from mechopt import buckling
from mechopt.sections import rectangle

E_STEEL = 200e9
SQ = rectangle(0.030, 0.030)  # I = 6.75e-8, A = 9e-4


def test_euler_load_pinned_pinned():
    assert buckling.euler_critical_load(E_STEEL, SQ.I, 0.8, K=1.0) == pytest.approx(208186.9678, rel=1e-6)


def test_euler_load_fixed_free():
    assert buckling.euler_critical_load(E_STEEL, SQ.I, 0.8, K=2.0) == pytest.approx(52046.7420, rel=1e-6)


def test_fixed_free_is_quarter_of_pinned():
    # P_cr ~ 1/K^2, so K=2 must give exactly 1/4 of K=1.
    p1 = buckling.euler_critical_load(E_STEEL, SQ.I, 0.8, K=1.0)
    p2 = buckling.euler_critical_load(E_STEEL, SQ.I, 0.8, K=2.0)
    assert p2 == pytest.approx(p1 / 4.0, rel=1e-12)


def test_longer_column_buckles_at_lower_load():
    short = buckling.euler_critical_load(E_STEEL, SQ.I, 0.8)
    long = buckling.euler_critical_load(E_STEEL, SQ.I, 1.6)
    assert long < short
    assert long == pytest.approx(short / 4.0, rel=1e-12)  # P_cr ~ 1/L^2


def test_radius_of_gyration_and_slenderness():
    assert buckling.radius_of_gyration(SQ) == pytest.approx(0.008660254, rel=1e-6)
    assert buckling.slenderness_ratio(0.8, SQ, K=1.0) == pytest.approx(92.3760, rel=1e-5)


def test_buckling_fos():
    pcr = buckling.euler_critical_load(E_STEEL, SQ.I, 0.8, K=1.0)
    assert buckling.buckling_factor_of_safety(50000.0, pcr) == pytest.approx(pcr / 50000.0, rel=1e-12)


@pytest.mark.parametrize("bad", [
    dict(E=-1, I=1e-7, L=1.0, K=1.0),
    dict(E=200e9, I=0, L=1.0, K=1.0),
    dict(E=200e9, I=1e-7, L=0, K=1.0),
    dict(E=200e9, I=1e-7, L=1.0, K=0),
])
def test_invalid_inputs_raise(bad):
    with pytest.raises(ValueError):
        buckling.euler_critical_load(**bad)
