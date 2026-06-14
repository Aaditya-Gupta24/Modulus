"""Geometry tests. Targets are exact closed-form values."""

import math
import pytest
from mechopt import sections


def test_rectangle():
    p = sections.rectangle(0.02, 0.02)
    assert p.A == pytest.approx(0.02 * 0.02)
    assert p.I == pytest.approx(0.02 * 0.02**3 / 12)
    assert p.I == pytest.approx(1.3333333e-08, rel=1e-5)
    assert p.c == pytest.approx(0.01)


def test_circle():
    p = sections.circle(0.03)
    assert p.A == pytest.approx(math.pi * 0.03**2 / 4)
    assert p.I == pytest.approx(math.pi * 0.03**4 / 64)
    assert p.I == pytest.approx(3.9760782e-08, rel=1e-5)
    assert p.c == pytest.approx(0.015)


def test_i_beam_reduces_to_rectangle_when_solid():
    # With tw == b, the void width is zero, so the I-beam is a solid rectangle.
    # Use non-degenerate flange thickness so web height remains positive.
    b, h = 0.04, 0.06
    solid = sections.rectangle(b, h)
    ibeam = sections.i_beam(b, h, tf=h / 6, tw=b)

    assert ibeam.I == pytest.approx(solid.I, rel=1e-9)
    assert ibeam.A == pytest.approx(solid.A, rel=1e-9)


def test_i_beam_is_stiffer_per_weight_than_solid():
    # An I-beam removes material near the neutral axis: less area, but I should
    # not collapse — sanity check that voids are subtracted, not added.
    b, h = 0.05, 0.10
    ibeam = sections.i_beam(b, h, tf=0.008, tw=0.006)
    solid = sections.rectangle(b, h)
    assert ibeam.A < solid.A
    assert ibeam.I < solid.I
    assert ibeam.I / ibeam.A > solid.I / solid.A


# ── square_tube tests ────────────────────────────────────────────────────────

def test_square_tube():
    p = sections.square_tube(0.040, 0.004)
    assert p.A == pytest.approx(5.760000e-4, rel=1e-4)
    assert p.I == pytest.approx(1.259520e-7, rel=1e-4)
    assert p.c == pytest.approx(0.020)


def test_square_tube_degenerates_to_solid():
    a = 0.040
    w = a / 2 - 1e-12
    tube = sections.square_tube(a, w)
    solid = sections.rectangle(a, a)
    assert tube.I == pytest.approx(solid.I, rel=1e-6)
    assert tube.A == pytest.approx(solid.A, rel=1e-6)


def test_square_tube_invalid_raises():
    with pytest.raises(ValueError):
        sections.square_tube(0.04, 0.0)      # w = 0
    with pytest.raises(ValueError):
        sections.square_tube(0.04, 0.02)     # 2*w = a
    with pytest.raises(ValueError):
        sections.square_tube(0.04, -0.001)   # w < 0


# ── hollow_rectangle tests ──────────────────────────────────────────────────

def test_hollow_rectangle():
    p = sections.hollow_rectangle(0.040, 0.060, 0.004)
    assert p.A == pytest.approx(7.36000e-4, rel=1e-4)
    assert p.I == pytest.approx(3.450453e-7, rel=1e-4)
    assert p.c == pytest.approx(0.030)


def test_hollow_rectangle_degenerates_to_solid():
    # w -> min(b,h)/2 means the inner void vanishes, matching a solid rectangle.
    b, h = 0.04, 0.06
    # w just under b/2 so 2*w < min(b, h) = b is still satisfied
    w = b / 2 - 1e-12
    hollow = sections.hollow_rectangle(b, h, w)
    solid = sections.rectangle(b, h)
    assert hollow.I == pytest.approx(solid.I, rel=1e-6)
    assert hollow.A == pytest.approx(solid.A, rel=1e-6)


def test_hollow_rectangle_invalid_raises():
    with pytest.raises(ValueError):
        sections.hollow_rectangle(0.04, 0.06, 0.0)     # w = 0
    with pytest.raises(ValueError):
        sections.hollow_rectangle(0.04, 0.06, 0.02)    # 2*w = h (not < min)
    with pytest.raises(ValueError):
        sections.hollow_rectangle(0.04, 0.06, -0.001)  # w < 0


# ── hollow_circle tests ─────────────────────────────────────────────────────

def test_hollow_circle():
    p = sections.hollow_circle(0.050, 0.042)
    assert p.A == pytest.approx(5.780530e-4, rel=1e-4)
    assert p.I == pytest.approx(1.540511e-7, rel=1e-4)
    assert p.c == pytest.approx(0.025)


def test_hollow_circle_di_zero_matches_solid():
    d = 0.050
    hollow = sections.hollow_circle(d, 0.0)
    solid = sections.circle(d)
    assert hollow.I == pytest.approx(solid.I, rel=1e-9)
    assert hollow.A == pytest.approx(solid.A, rel=1e-9)


def test_hollow_circle_invalid_raises():
    with pytest.raises(ValueError):
        sections.hollow_circle(0.05, 0.05)   # di == d
    with pytest.raises(ValueError):
        sections.hollow_circle(0.05, 0.06)   # di > d
    with pytest.raises(ValueError):
        sections.hollow_circle(0.05, -0.01)  # di < 0
