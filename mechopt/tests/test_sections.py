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
    # With tw == b and tf == h/2 the section is a solid rectangle.
    b, h = 0.04, 0.06
    solid = sections.rectangle(b, h)
    ibeam = sections.i_beam(b, h, tf=h / 2, tw=b)
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
