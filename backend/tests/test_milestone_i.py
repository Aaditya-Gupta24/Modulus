"""Milestone I oracle-first tests: UDL load cases, shear stress, local buckling.

All numeric targets were hand-derived from first-principles equations by the
mechanics analyst.  NEVER edit a target to make a test pass — fix the code.

Oracle derivations are documented inline next to each assert.
"""

import math
import pytest
from modulus import sections, beam
from modulus.materials import MATERIALS

# ---------------------------------------------------------------------------
# Shared fixtures / setup helpers
# ---------------------------------------------------------------------------

# Case A — Steel A36, solid rectangle 30×30 mm, L=0.8 m, P=300 N
STEEL = MATERIALS["steel_a36"]       # E=200 GPa, sigma_y=250 MPa
RECT_30 = sections.rectangle(0.03, 0.03)
# I = 0.03 * 0.03**3 / 12 = 6.75e-8 m^4, c = 0.015 m

# Case B — Aluminum 6061, solid circle d=30 mm, L=1.2 m, P=800 N
AL = MATERIALS["aluminum_6061"]      # E=69 GPa, sigma_y=275 MPa
CIRC_30 = sections.circle(0.03)
# I = pi*0.03**4/64 = 3.97608e-8 m^4, c = 0.015 m


# ===========================================================================
# UDL load-case tests
# ===========================================================================

class TestCantileverUDLMoment:
    """Case A: cantilever_udl, P=300 N, L=0.8 m.
    M = P*L/2 = 300*0.8/2 = 120 N·m
    """
    def test_cantilever_udl_moment(self):
        M = beam.max_moment(300.0, 0.8, "cantilever_udl")
        assert M == pytest.approx(120.0)


class TestCantileverUDLStress:
    """Case A: sigma = M*c/I = 120*0.015/6.75e-8 = 26,666,667 Pa"""
    def test_cantilever_udl_stress(self):
        M = beam.max_moment(300.0, 0.8, "cantilever_udl")
        sigma = beam.max_stress(M, RECT_30)
        assert sigma == pytest.approx(26_666_667.0, rel=1e-4)


class TestCantileverUDLDeflection:
    """Case A: delta = P*L^3 / (8*E*I)
    = 300 * 0.8^3 / (8 * 200e9 * 6.75e-8)
    = 300 * 0.512 / (8 * 13.5)
    = 153.6 / 108
    = 1.4222...e-3 m  →  0.001422 m
    """
    def test_cantilever_udl_deflection(self):
        delta = beam.max_deflection(300.0, 0.8, STEEL.E, RECT_30, "cantilever_udl")
        assert delta == pytest.approx(0.001422, rel=1e-3)


class TestCantileverUDLFoS:
    """Case A: FoS = sigma_y / sigma = 250e6 / 26,666,667 = 9.375"""
    def test_cantilever_udl_fos(self):
        M = beam.max_moment(300.0, 0.8, "cantilever_udl")
        sigma = beam.max_stress(M, RECT_30)
        fos = beam.factor_of_safety(sigma, STEEL.sigma_y)
        assert fos == pytest.approx(9.375, rel=1e-4)


class TestSimplyUDLMoment:
    """Case B: simply_udl, P=800 N, L=1.2 m.
    M = P*L/8 = 800*1.2/8 = 120 N·m
    """
    def test_simply_udl_moment(self):
        M = beam.max_moment(800.0, 1.2, "simply_udl")
        assert M == pytest.approx(120.0)


class TestSimplyUDLStress:
    """Case B: sigma = M*c/I
    I = pi*0.03^4/64 = 3.97608e-8 m^4, c = 0.015 m
    sigma = 120*0.015 / 3.97608e-8 = 1.8 / 3.97608e-8 = 45,270,677 Pa
    """
    def test_simply_udl_stress(self):
        M = beam.max_moment(800.0, 1.2, "simply_udl")
        sigma = beam.max_stress(M, CIRC_30)
        assert sigma == pytest.approx(45_270_677.0, rel=1e-3)


class TestSimplyUDLDeflection:
    """Case B: delta = 5*P*L^3 / (384*E*I)
    = 5*800*1.728 / (384*69e9*3.97608e-8)
    = 6912 / (384*2741.5)
    = 6912 / 1,052,736
    ≈ 0.006561 m
    """
    def test_simply_udl_deflection(self):
        delta = beam.max_deflection(800.0, 1.2, AL.E, CIRC_30, "simply_udl")
        assert delta == pytest.approx(0.006561, rel=1e-3)


class TestSimplyUDLFoS:
    """Case B: FoS = sigma_y / sigma = 275e6 / 45,270,677 = 6.0746"""
    def test_simply_udl_fos(self):
        M = beam.max_moment(800.0, 1.2, "simply_udl")
        sigma = beam.max_stress(M, CIRC_30)
        fos = beam.factor_of_safety(sigma, AL.sigma_y)
        assert fos == pytest.approx(6.0746, rel=1e-3)


class TestUDLInvalidLoadCase:
    """Unknown load case must raise ValueError from both max_moment and max_deflection."""
    def test_max_moment_invalid_raises(self):
        with pytest.raises(ValueError):
            beam.max_moment(300.0, 0.8, "unknown_case")

    def test_max_deflection_invalid_raises(self):
        with pytest.raises(ValueError):
            beam.max_deflection(300.0, 0.8, STEEL.E, RECT_30, "unknown_case")


# ===========================================================================
# Shear force tests
# ===========================================================================

class TestMaxShear:
    """max_shear returns the reaction (support) shear at the critical section.

    cantilever_end / cantilever_udl : V = P
    simply_center  / simply_udl     : V = P/2
    """

    def test_max_shear_cantilever_end(self):
        # Case C — P=300 N, cantilever_end → V = 300
        assert beam.max_shear(300.0, "cantilever_end") == pytest.approx(300.0)

    def test_max_shear_cantilever_udl(self):
        # P=300 N, cantilever_udl → V = P = 300
        assert beam.max_shear(300.0, "cantilever_udl") == pytest.approx(300.0)

    def test_max_shear_simply_center(self):
        # Case D — P=800 N, simply_center → V = P/2 = 400
        assert beam.max_shear(800.0, "simply_center") == pytest.approx(400.0)

    def test_max_shear_simply_udl(self):
        # P=800 N, simply_udl → V = P/2 = 400
        assert beam.max_shear(800.0, "simply_udl") == pytest.approx(400.0)


# ===========================================================================
# Shear shape factor tests
# ===========================================================================

class TestShearShapeFactor:
    """shear_shape_factor returns the correct k for each section type.

    rectangle  : k = 1.5     (exact for solid rectangle)
    circle     : k = 4/3     (exact for solid circle)
    other      : k = 1.5     (conservative approximation)
    """

    def test_shear_shape_factor_rect(self):
        assert beam.shear_shape_factor("rectangle") == pytest.approx(1.5)

    def test_shear_shape_factor_circle(self):
        assert beam.shear_shape_factor("circle") == pytest.approx(4.0 / 3.0)

    def test_shear_shape_factor_default_tube(self):
        # Thin-walled / I-beam / unrecognised → conservative 1.5
        assert beam.shear_shape_factor("square_tube") == pytest.approx(1.5)


# ===========================================================================
# Shear stress and shear FoS tests
# ===========================================================================

class TestShearStressRect:
    """Case C — Steel A36, rect 30×30 mm, V=300 N.
    A = 0.03*0.03 = 9e-4 m^2, k = 1.5
    tau = 1.5*300/9e-4 = 450/9e-4 = 500,000 Pa
    tau_allow = 0.6*250e6 = 150e6 Pa
    shear_FoS = 150e6/500,000 = 300.0
    """

    def test_shear_stress_rect(self):
        V = beam.max_shear(300.0, "cantilever_end")
        tau = beam.max_shear_stress(V, RECT_30.A, "rectangle")
        assert tau == pytest.approx(500_000.0)

    def test_shear_fos_rect(self):
        V = beam.max_shear(300.0, "cantilever_end")
        tau = beam.max_shear_stress(V, RECT_30.A, "rectangle")
        fos = beam.shear_fos(tau, STEEL.sigma_y)
        assert fos == pytest.approx(300.0)


class TestShearStressCircle:
    """Case D — Al 6061, circle d=30 mm, V=400 N.
    A = pi*(0.03^2)/4 = 7.06858e-4 m^2, k = 4/3
    tau = (4/3)*400/7.06858e-4 = 533.333/7.06858e-4 = 754,623 Pa
    tau_allow = 0.6*275e6 = 165e6 Pa
    shear_FoS = 165e6/754,623 = 218.68
    """

    def test_shear_stress_circle(self):
        V = beam.max_shear(800.0, "simply_center")   # = 400 N
        tau = beam.max_shear_stress(V, CIRC_30.A, "circle")
        assert tau == pytest.approx(754_623.0, rel=1e-3)

    def test_shear_fos_circle(self):
        V = beam.max_shear(800.0, "simply_center")
        tau = beam.max_shear_stress(V, CIRC_30.A, "circle")
        fos = beam.shear_fos(tau, AL.sigma_y)
        assert fos == pytest.approx(218.68, rel=1e-2)


# ===========================================================================
# Local buckling tests
# ===========================================================================

class TestLocalBucklingSquareTube:
    """Case E — square_tube a=40 mm, w=2 mm, Steel A36.

    lambda      = (a - 2*w) / w = (40 - 4) / 2 = 36/2 = 18
    lambda_limit = 1.12 * sqrt(E / sigma_y)
               = 1.12 * sqrt(200e9 / 250e6)
               = 1.12 * sqrt(800)
               = 1.12 * 28.2843
               = 31.678
    Compact: 18 < 31.678 → True
    """
    DIMS = {"a": 0.040, "w": 0.002}

    def test_slenderness(self):
        lam = beam.local_buckling_slenderness("square_tube", self.DIMS)
        assert lam == pytest.approx(18.0)

    def test_limit(self):
        limit = beam.local_buckling_limit("square_tube", STEEL.E, STEEL.sigma_y)
        # 1.12 * sqrt(200e9/250e6) = 1.12 * 28.2843 = 31.678
        assert limit == pytest.approx(31.678, rel=1e-3)

    def test_compact_true(self):
        ok = beam.local_buckling_ok("square_tube", self.DIMS, STEEL.E, STEEL.sigma_y)
        assert ok is True

    def test_noncompact_thin_wall(self):
        """Very thin wall: a=40 mm, w=0.5 mm → lambda = (40-1)/0.5 = 78 > 31.678."""
        dims = {"a": 0.040, "w": 0.0005}
        ok = beam.local_buckling_ok("square_tube", dims, STEEL.E, STEEL.sigma_y)
        assert ok is False


class TestLocalBucklingHollowCircle:
    """Case F — hollow_circle d=50 mm, wall t=2 mm, Steel A36.

    D/t       = 50/2 = 25
    D/t_limit = 0.07 * E / sigma_y = 0.07 * 200e9 / 250e6 = 56.0
    Compact: 25 < 56.0 → True
    """
    DIMS = {"d": 0.050, "t": 0.002}

    def test_slenderness(self):
        lam = beam.local_buckling_slenderness("hollow_circle", self.DIMS)
        assert lam == pytest.approx(25.0)

    def test_limit(self):
        limit = beam.local_buckling_limit("hollow_circle", STEEL.E, STEEL.sigma_y)
        assert limit == pytest.approx(56.0)

    def test_compact_true(self):
        ok = beam.local_buckling_ok("hollow_circle", self.DIMS, STEEL.E, STEEL.sigma_y)
        assert ok is True


class TestLocalBucklingSolidSections:
    """Solid sections have no local buckling — all functions must return None."""

    def test_solid_rectangle_slenderness_none(self):
        lam = beam.local_buckling_slenderness("rectangle", {})
        assert lam is None

    def test_solid_circle_slenderness_none(self):
        lam = beam.local_buckling_slenderness("circle", {})
        assert lam is None

    def test_solid_rectangle_limit_none(self):
        limit = beam.local_buckling_limit("rectangle", STEEL.E, STEEL.sigma_y)
        assert limit is None

    def test_solid_circle_limit_none(self):
        limit = beam.local_buckling_limit("circle", STEEL.E, STEEL.sigma_y)
        assert limit is None

    def test_solid_rectangle_ok_none(self):
        ok = beam.local_buckling_ok("rectangle", {}, STEEL.E, STEEL.sigma_y)
        assert ok is None

    def test_solid_circle_ok_none(self):
        ok = beam.local_buckling_ok("circle", {}, STEEL.E, STEEL.sigma_y)
        assert ok is None
