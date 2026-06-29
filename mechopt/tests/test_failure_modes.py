"""Oracle-first tests for the failure_modes module.

These tests encode hand-derived oracle targets for three reference beams.
The module under test does NOT exist yet — importing it will fail until
failure_modes.py is implemented.  That is intentional (red-green-refactor).

Oracle derivations are documented inline next to each assertion.
"""

import pytest
from mechopt import sections
from mechopt.materials import MATERIALS
from mechopt.failure_modes import (
    CheckResult,
    SafetyCase,
    Status,
    evaluate_candidate,
)


# ---------------------------------------------------------------------------
# Helpers — material / section shortcuts used across multiple tests
# ---------------------------------------------------------------------------

def _beam_a():
    """Steel A36, rectangle 30x30 mm, L=0.8 m, P=300 N, cantilever_end."""
    return dict(
        material=MATERIALS["steel_a36"],
        section_fn=sections.rectangle,
        dims=(0.030, 0.030),
        load=300.0,
        length=0.8,
        load_case="cantilever_end",
        fos_target=1.5,
        deflection_limit=0.010,
        compression_load=300.0,
        K=2.0,  # cantilever effective-length factor
    )


def _beam_b():
    """Aluminum 6061, circle d=30 mm, L=1.2 m, P=800 N, simply_center."""
    return dict(
        material=MATERIALS["aluminum_6061"],
        section_fn=sections.circle,
        dims=(0.030,),
        load=800.0,
        length=1.2,
        load_case="simply_center",
        fos_target=1.5,
        deflection_limit=0.010,
        compression_load=800.0,
        K=1.0,  # simply-supported effective-length factor
    )


def _beam_c():
    """ABS plastic, rectangle 10x10 mm, L=1.0 m, P=500 N, cantilever_end."""
    return dict(
        material=MATERIALS["abs_plastic"],
        section_fn=sections.rectangle,
        dims=(0.010, 0.010),
        load=500.0,
        length=1.0,
        load_case="cantilever_end",
        fos_target=1.5,
        deflection_limit=0.010,
        compression_load=500.0,
        K=2.0,
    )


def _find_check(sc: SafetyCase, name: str) -> CheckResult:
    """Return the CheckResult with the given name from a SafetyCase."""
    for c in sc.checks:
        if c.name == name:
            return c
    raise KeyError(f"No check named '{name}' in SafetyCase")


# ---------------------------------------------------------------------------
# 1. Basic dataclass construction
# ---------------------------------------------------------------------------

def test_check_result_creation():
    """CheckResult can be instantiated and exposes expected fields."""
    cr = CheckResult(
        name="bending_stress",
        actual=100e6,
        allowable=250e6,
        margin=0.6,
        status=Status.PASS,
        notes="test",
    )
    assert cr.name == "bending_stress"
    assert cr.actual == pytest.approx(100e6)
    assert cr.allowable == pytest.approx(250e6)
    assert cr.margin == pytest.approx(0.6)
    assert cr.status is Status.PASS
    assert cr.notes == "test"


# ---------------------------------------------------------------------------
# 2. Beam A — all checks pass
# ---------------------------------------------------------------------------

def test_beam_a_all_pass():
    """Steel A36 rect 30x30, cantilever, P=300 N, L=0.8 m — everything passes."""
    sc = evaluate_candidate(**_beam_a())

    # -- bending_stress --
    # M = P*L = 300*0.8 = 240 N-m
    # I = b*h^3/12 = 0.03*0.03^3/12 = 6.75e-8 m^4
    # c = h/2 = 0.015 m
    # sigma = M*c/I = 240*0.015/6.75e-8 = 5.33333e7 Pa
    # margin = (250e6 - 5.33333e7) / 250e6 = 0.78667
    bs = _find_check(sc, "bending_stress")
    assert bs.actual == pytest.approx(5.33333e7, rel=1e-3)
    assert bs.allowable == pytest.approx(250e6, rel=1e-3)
    assert bs.margin == pytest.approx(0.78667, rel=1e-3)
    assert bs.status is Status.PASS

    # -- deflection --
    # delta = P*L^3/(3*E*I) = 300*0.8^3/(3*200e9*6.75e-8) = 3.79259e-3 m
    # margin = (0.010 - 3.79259e-3) / 0.010 = 0.62074
    defl = _find_check(sc, "deflection")
    assert defl.actual == pytest.approx(3.79259e-3, rel=1e-3)
    assert defl.allowable == pytest.approx(0.010, rel=1e-3)
    assert defl.margin == pytest.approx(0.62074, rel=1e-3)
    assert defl.status is Status.PASS

    # -- yield_fos --
    # fos = sigma_y / sigma = 250e6 / 5.33333e7 = 4.6875
    # margin = (4.6875 - 1.5) / 1.5 = 2.125
    fos = _find_check(sc, "yield_fos")
    assert fos.actual == pytest.approx(4.6875, rel=1e-3)
    assert fos.allowable == pytest.approx(1.5, rel=1e-3)
    assert fos.margin == pytest.approx(2.125, rel=1e-3)
    assert fos.status is Status.PASS

    # -- euler_buckling --
    # A = 0.03*0.03 = 9e-4 m^2
    # Le = K*L = 2.0*0.8 = 1.6 m
    # P_cr = pi^2*E*I / Le^2 = pi^2*200e9*6.75e-8 / 1.6^2 = 52048 N  (approx)
    # buckling_fos = P_cr / P = 52048 / 300 = 173.49
    # margin = (173.49 - 1.0) / 1.0 = 172.49
    buck = _find_check(sc, "euler_buckling")
    assert buck.actual == pytest.approx(173.49, rel=1e-3)
    assert buck.margin == pytest.approx(172.49, rel=1e-3)
    assert buck.status is Status.PASS

    # -- overall --
    assert sc.overall_status is Status.PASS
    # Deflection has the lowest margin (0.6207) among the modeled checks
    assert sc.controlling_check == "deflection"
    assert sc.failure_reasons == []


# ---------------------------------------------------------------------------
# 3. Beam B — deflection fails, others pass
# ---------------------------------------------------------------------------

def test_beam_b_deflection_fail():
    """Aluminum 6061 circle d=30, simply_center, P=800 N, L=1.2 m — deflection fails."""
    sc = evaluate_candidate(**_beam_b())

    # -- bending_stress --
    # M = P*L/4 = 800*1.2/4 = 240 N-m
    # I = pi*d^4/64 = pi*0.03^4/64 = 3.97608e-8 m^4
    # c = d/2 = 0.015 m
    # sigma = M*c/I = 240*0.015/3.97608e-8 = 9.0541e7 Pa
    # margin = (275e6 - 9.0541e7) / 275e6 = 0.67076
    bs = _find_check(sc, "bending_stress")
    assert bs.actual == pytest.approx(9.0541e7, rel=1e-3)
    assert bs.allowable == pytest.approx(275e6, rel=1e-3)
    assert bs.margin == pytest.approx(0.67076, rel=1e-3)
    assert bs.status is Status.PASS

    # -- deflection --
    # delta = P*L^3/(48*E*I) = 800*1.2^3/(48*69e9*3.97608e-8) = 1.0498e-2 m
    # margin = (0.010 - 1.0498e-2) / 0.010 = -0.04986
    defl = _find_check(sc, "deflection")
    assert defl.actual == pytest.approx(1.0498e-2, rel=1e-3)
    assert defl.allowable == pytest.approx(0.010, rel=1e-3)
    # Near-zero margin: use abs tolerance to avoid relative amplification
    assert defl.margin == pytest.approx(-0.0498, abs=2e-3)
    assert defl.status is Status.FAIL

    # -- yield_fos --
    # fos = 275e6 / 9.0541e7 = 3.0373
    # margin = (3.0373 - 1.5) / 1.5 = 1.0249
    fos = _find_check(sc, "yield_fos")
    assert fos.actual == pytest.approx(3.0373, rel=1e-3)
    assert fos.margin == pytest.approx(1.0249, rel=1e-3)
    assert fos.status is Status.PASS

    # -- euler_buckling --
    # Le = 1.0*1.2 = 1.2 m
    # P_cr = pi^2*69e9*3.97608e-8 / 1.2^2 = 18804 N  (approx)
    # buckling_fos = 18804 / 800 = 23.505
    # margin = (23.505 - 1.0) / 1.0 = 22.505
    buck = _find_check(sc, "euler_buckling")
    assert buck.actual == pytest.approx(23.505, rel=1e-3)
    assert buck.margin == pytest.approx(22.505, rel=1e-3)
    assert buck.status is Status.PASS

    # -- overall --
    assert sc.overall_status is Status.FAIL
    assert sc.controlling_check == "deflection"
    assert "deflection" in sc.failure_reasons


# ---------------------------------------------------------------------------
# 4. Beam C — everything fails
# ---------------------------------------------------------------------------

def test_beam_c_all_fail():
    """ABS plastic rect 10x10, cantilever, P=500 N, L=1.0 m — all checks fail."""
    sc = evaluate_candidate(**_beam_c())

    # -- bending_stress --
    # M = P*L = 500*1.0 = 500 N-m
    # I = 0.01*0.01^3/12 = 8.3333e-10 m^4
    # c = 0.005 m
    # sigma = 500*0.005/8.3333e-10 = 3.0e9 Pa
    # margin = (40e6 - 3.0e9) / 40e6 = -74.0
    bs = _find_check(sc, "bending_stress")
    assert bs.actual == pytest.approx(3.0e9, rel=1e-3)
    assert bs.allowable == pytest.approx(4.0e7, rel=1e-3)
    assert bs.margin == pytest.approx(-74.0, rel=1e-3)
    assert bs.status is Status.FAIL

    # -- deflection --
    # delta = P*L^3/(3*E*I) = 500*1.0/(3*2.3e9*8.3333e-10) = 86.957 m
    # margin = (0.010 - 86.957) / 0.010 = -8694.65 (approx)
    defl = _find_check(sc, "deflection")
    assert defl.actual == pytest.approx(86.957, rel=1e-3)
    assert defl.margin == pytest.approx(-8694.65, rel=1e-2)
    assert defl.status is Status.FAIL

    # -- yield_fos --
    # fos = 40e6 / 3.0e9 = 0.01333
    # margin = (0.01333 - 1.5) / 1.5 = -0.99111
    fos = _find_check(sc, "yield_fos")
    assert fos.actual == pytest.approx(0.01333, rel=1e-3)
    assert fos.margin == pytest.approx(-0.99111, rel=1e-3)
    assert fos.status is Status.FAIL

    # -- euler_buckling --
    # Le = 2.0*1.0 = 2.0 m
    # P_cr = pi^2*2.3e9*8.3333e-10 / 2.0^2 = 4.729 N  (approx)
    # buckling_fos = 4.729 / 500 = 0.009458
    # margin = (0.009458 - 1.0) / 1.0 = -0.99054
    buck = _find_check(sc, "euler_buckling")
    assert buck.actual == pytest.approx(0.009458, rel=1e-3)
    assert buck.margin == pytest.approx(-0.99054, rel=1e-3)
    assert buck.status is Status.FAIL

    # -- overall --
    assert sc.overall_status is Status.FAIL
    # Deflection has the most negative margin (-8694.65)
    assert sc.controlling_check == "deflection"
    # All four modeled checks should appear in failure_reasons
    assert "bending_stress" in sc.failure_reasons
    assert "deflection" in sc.failure_reasons
    assert "yield_fos" in sc.failure_reasons
    assert "euler_buckling" in sc.failure_reasons


# ---------------------------------------------------------------------------
# 5. Shear and torsion are not modeled
# ---------------------------------------------------------------------------

def test_shear_torsion_not_modeled():
    """Shear and torsion checks exist in the result but are flagged NOT_MODELED."""
    sc = evaluate_candidate(**_beam_a())

    shear = _find_check(sc, "shear")
    assert shear.status is Status.NOT_MODELED

    torsion = _find_check(sc, "torsion")
    assert torsion.status is Status.NOT_MODELED


# ---------------------------------------------------------------------------
# 6. No deflection limit — deflection check skipped, overall passes
# ---------------------------------------------------------------------------

def test_no_deflection_limit():
    """Beam B without a deflection limit should pass overall (no deflection check)."""
    kwargs = _beam_b()
    kwargs["deflection_limit"] = None

    sc = evaluate_candidate(**kwargs)

    # Without the deflection constraint, all remaining checks pass for Beam B
    assert sc.overall_status is Status.PASS

    # Deflection check should not appear in the results
    defl_checks = [c for c in sc.checks if c.name == "deflection"]
    assert len(defl_checks) == 0


# ---------------------------------------------------------------------------
# 7. Warning status — margin positive but below 10 %
# ---------------------------------------------------------------------------

def test_warning_status():
    """Beam B with deflection_limit=0.0108 m triggers a WARNING on deflection.

    The margin is small but positive, so the check should be WARNING (0 < margin < 0.10).
    """
    kwargs = _beam_b()
    kwargs["deflection_limit"] = 0.0108  # just above actual deflection of ~0.01050

    sc = evaluate_candidate(**kwargs)

    # -- deflection --
    # actual = 1.0498e-2 m (same as Beam B)
    # margin = (0.0108 - 0.01050) / 0.0108 = 0.02778  (approx, within 0-0.10 band)
    defl = _find_check(sc, "deflection")
    assert defl.actual == pytest.approx(1.0498e-2, rel=1e-3)
    assert defl.margin == pytest.approx(0.028, rel=5e-2)  # ~2.8 %, triggers warning
    assert defl.status is Status.WARNING

    # Overall should be WARNING (no failures, but a warning exists)
    assert sc.overall_status is Status.WARNING


# ---------------------------------------------------------------------------
# 8. Optimizer integration — SafetyCase attached to every candidate row
# ---------------------------------------------------------------------------

def test_optimizer_attaches_safety_case():
    """evaluate_candidates attaches a SafetyCase to every row."""
    from mechopt.optimizer import evaluate_candidates
    df = evaluate_candidates(
        load=300.0, length=0.8, load_case="cantilever_end", fos_target=1.5,
        material_keys=["steel_a36"], section_types=["rectangle"],
        deflection_limit=0.010,
    )
    assert len(df) > 0
    for _, row in df.iterrows():
        sc = row["safety_case"]
        assert isinstance(sc, SafetyCase)
        assert len(sc.checks) >= 4  # bending_stress, deflection, yield_fos, euler_buckling + shear + torsion
        assert sc.overall_status in (Status.PASS, Status.FAIL, Status.WARNING)
        assert sc.controlling_check  # non-empty string


# ---------------------------------------------------------------------------
# 9. SafetyCase matches oracle Beam A (steel rect 30x30 mm)
# ---------------------------------------------------------------------------

def test_safety_case_matches_oracle_beam_a():
    """SafetyCase for steel rect 30x30 in optimizer output matches Beam A oracle."""
    from mechopt.optimizer import evaluate_candidates
    df = evaluate_candidates(
        load=300.0, length=0.8, load_case="cantilever_end", fos_target=1.5,
        material_keys=["steel_a36"], section_types=["rectangle"],
        deflection_limit=0.010,
    )
    # Find the 30x30 mm candidate
    row_30 = df[df["dims"] == "30x30 mm"].iloc[0]
    sc = row_30["safety_case"]

    # Overall should pass
    assert sc.overall_status is Status.PASS
    assert sc.controlling_check == "deflection"
    assert sc.failure_reasons == []

    # Check names should include all expected checks
    check_names = [c.name for c in sc.checks]
    assert "bending_stress" in check_names
    assert "deflection" in check_names
    assert "yield_fos" in check_names
    assert "euler_buckling" in check_names
    assert "shear" in check_names
    assert "torsion" in check_names


# ---------------------------------------------------------------------------
# 10. Shear and torsion are NOT_MODELED in optimizer output
# ---------------------------------------------------------------------------

def test_safety_case_has_not_modeled_checks():
    """Shear and torsion are NOT_MODELED in optimizer SafetyCase output."""
    from mechopt.optimizer import evaluate_candidates
    df = evaluate_candidates(
        load=300.0, length=0.8, load_case="cantilever_end", fos_target=1.5,
        material_keys=["steel_a36"], section_types=["rectangle"],
    )
    sc = df.iloc[0]["safety_case"]
    shear = [c for c in sc.checks if c.name == "shear"][0]
    torsion = [c for c in sc.checks if c.name == "torsion"][0]
    assert shear.status is Status.NOT_MODELED
    assert torsion.status is Status.NOT_MODELED
