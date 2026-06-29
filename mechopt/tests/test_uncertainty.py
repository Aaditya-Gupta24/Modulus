"""Monte Carlo uncertainty analysis tests."""

import pytest
import numpy as np
from mechopt.uncertainty import run_monte_carlo, MonteCarloResult, reliability_summary


def test_returns_correct_type():
    r = run_monte_carlo("steel_a36", "rectangle", 30, 500, 1.0,
                        "cantilever_end", seed=42)
    assert isinstance(r, MonteCarloResult)


def test_n_samples_matches():
    r = run_monte_carlo("steel_a36", "rectangle", 30, 500, 1.0,
                        "cantilever_end", n_samples=500, seed=42)
    assert r.n_samples == 500


def test_deterministic_with_seed():
    """Same seed → same results."""
    r1 = run_monte_carlo("steel_a36", "rectangle", 30, 500, 1.0,
                         "cantilever_end", seed=123)
    r2 = run_monte_carlo("steel_a36", "rectangle", 30, 500, 1.0,
                         "cantilever_end", seed=123)
    assert r1.fos_mean == pytest.approx(r2.fos_mean)
    assert r1.failure_probability == pytest.approx(r2.failure_probability)


def test_fos_mean_near_nominal():
    """Mean FoS should be near the nominal 2.25 (Steel A36, rect 30mm, cantilever)."""
    r = run_monte_carlo("steel_a36", "rectangle", 30, 500, 1.0,
                        "cantilever_end", n_samples=2000, seed=42)
    assert r.fos_mean == pytest.approx(2.25, rel=0.1)


def test_fos_std_positive():
    r = run_monte_carlo("steel_a36", "rectangle", 30, 500, 1.0,
                        "cantilever_end", seed=42)
    assert r.fos_std > 0


def test_percentiles_ordered():
    r = run_monte_carlo("steel_a36", "rectangle", 30, 500, 1.0,
                        "cantilever_end", seed=42)
    assert r.fos_p5 < r.fos_mean < r.fos_p95


def test_failure_probability_between_0_and_1():
    r = run_monte_carlo("steel_a36", "rectangle", 30, 500, 1.0,
                        "cantilever_end", seed=42)
    assert 0 <= r.failure_probability <= 1


def test_zero_cov_gives_zero_std():
    """No perturbation → no variation."""
    r = run_monte_carlo("steel_a36", "rectangle", 30, 500, 1.0,
                        "cantilever_end", n_samples=100, seed=42,
                        load_cov=0, dimension_cov=0, E_cov=0, sigma_y_cov=0)
    assert r.fos_std == pytest.approx(0, abs=1e-10)
    assert r.failure_probability == 0.0  # nominal FoS=2.25 > 2.0


def test_high_cov_increases_failure_prob():
    """High uncertainty → higher failure probability."""
    r_low = run_monte_carlo("steel_a36", "rectangle", 30, 500, 1.0,
                            "cantilever_end", n_samples=2000, seed=42,
                            load_cov=0.05, dimension_cov=0.01)
    r_high = run_monte_carlo("steel_a36", "rectangle", 30, 500, 1.0,
                             "cantilever_end", n_samples=2000, seed=42,
                             load_cov=0.30, dimension_cov=0.10)
    assert r_high.failure_probability >= r_low.failure_probability


def test_samples_dict_has_arrays():
    r = run_monte_carlo("steel_a36", "rectangle", 30, 500, 1.0,
                        "cantilever_end", n_samples=100, seed=42)
    assert "fos" in r.samples
    assert "stress" in r.samples
    assert "deflection" in r.samples
    assert len(r.samples["fos"]) == 100


def test_reliability_summary_string():
    r = run_monte_carlo("steel_a36", "rectangle", 30, 500, 1.0,
                        "cantilever_end", seed=42)
    s = reliability_summary(r)
    assert "Monte Carlo" in s
    assert "P(fail)" in s


def test_circle_section():
    r = run_monte_carlo("steel_a36", "circle", 30, 500, 1.0,
                        "cantilever_end", seed=42)
    assert r.fos_mean > 0


def test_simply_supported():
    r = run_monte_carlo("aluminum_6061", "rectangle", 30, 500, 1.0,
                        "simply_center", seed=42)
    assert r.fos_mean > 0
