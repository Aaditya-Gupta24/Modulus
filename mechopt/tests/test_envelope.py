"""Load-case envelope tests — oracle-first known-answer cases."""

import pytest
from mechopt.envelope import evaluate_envelope, EnvelopeResult, EnvelopeCase


# Steel A36 rectangle 30x30mm
# I = 0.03^4/12 = 6.75e-8, c = 0.015

# Case 1: cantilever, P=500, L=1.0
#   M = 500*1.0 = 500 N·m
#   sigma = 500*0.015/6.75e-8 = 111,111,111 Pa
#   fos = 250e6/111,111,111 = 2.25
#   delta = 500*1.0^3/(3*200e9*6.75e-8) = 0.01235 m

# Case 2: simply supported, P=500, L=1.0
#   M = 500*1.0/4 = 125 N·m
#   sigma = 125*0.015/6.75e-8 = 27,777,778 Pa
#   fos = 250e6/27,777,778 = 9.0
#   delta = 500*1.0^3/(48*200e9*6.75e-8) = 0.000772 m

_CASES = [
    {"name": "Cantilever end", "load": 500.0, "length": 1.0, "load_case": "cantilever_end"},
    {"name": "Simply center", "load": 500.0, "length": 1.0, "load_case": "simply_center"},
]


def test_envelope_returns_correct_type():
    result = evaluate_envelope("steel_a36", "rectangle", 30.0, _CASES, fos_target=2.0)
    assert isinstance(result, EnvelopeResult)


def test_envelope_has_two_cases():
    result = evaluate_envelope("steel_a36", "rectangle", 30.0, _CASES, fos_target=2.0)
    assert len(result.cases) == 2


def test_cantilever_governs():
    """Cantilever has lower FoS (2.25) than simply supported (9.0)."""
    result = evaluate_envelope("steel_a36", "rectangle", 30.0, _CASES, fos_target=2.0)
    assert result.governing_case == "Cantilever end"


def test_governing_fos():
    result = evaluate_envelope("steel_a36", "rectangle", 30.0, _CASES, fos_target=2.0)
    assert result.governing_fos == pytest.approx(2.25, rel=1e-3)


def test_cantilever_stress():
    """sigma = 500*0.015/6.75e-8 = 111.11 MPa."""
    result = evaluate_envelope("steel_a36", "rectangle", 30.0, _CASES, fos_target=2.0)
    cantilever = [c for c in result.cases if c.load_case == "Cantilever end"][0]
    assert cantilever.stress == pytest.approx(111_111_111, rel=1e-3)


def test_simply_supported_fos():
    """FoS = 250e6 / 27,777,778 = 9.0."""
    result = evaluate_envelope("steel_a36", "rectangle", 30.0, _CASES, fos_target=2.0)
    ss = [c for c in result.cases if c.load_case == "Simply center"][0]
    assert ss.fos == pytest.approx(9.0, rel=1e-3)


def test_all_safe_when_both_pass():
    result = evaluate_envelope("steel_a36", "rectangle", 30.0, _CASES, fos_target=2.0)
    assert result.all_safe is True


def test_all_safe_false_when_target_high():
    """FoS target 5.0: cantilever FoS=2.25 fails, simply supported FoS=9.0 passes."""
    result = evaluate_envelope("steel_a36", "rectangle", 30.0, _CASES, fos_target=5.0)
    assert result.all_safe is False


def test_governing_deflection():
    """Cantilever has worst deflection: 0.01235 m."""
    result = evaluate_envelope("steel_a36", "rectangle", 30.0, _CASES, fos_target=2.0)
    assert result.governing_deflection == pytest.approx(0.01235, rel=1e-2)


def test_summary_contains_governing():
    result = evaluate_envelope("steel_a36", "rectangle", 30.0, _CASES, fos_target=2.0)
    assert "Cantilever end" in result.summary


def test_single_case_works():
    cases = [{"name": "Single", "load": 500.0, "length": 1.0, "load_case": "cantilever_end"}]
    result = evaluate_envelope("steel_a36", "rectangle", 30.0, cases, fos_target=2.0)
    assert len(result.cases) == 1
    assert result.governing_case == "Single"


def test_invalid_geometry_raises():
    with pytest.raises(ValueError):
        evaluate_envelope("steel_a36", "nonexistent_section", 30.0,
                          [{"name": "x", "load": 500, "length": 1, "load_case": "cantilever_end"}])
