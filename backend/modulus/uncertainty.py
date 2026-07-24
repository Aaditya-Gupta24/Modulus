"""Monte Carlo / uncertainty analysis for Modulus (Milestone H).

Runs Monte Carlo simulations on a single beam design by perturbing input
parameters according to specified coefficients of variation (CoV), then
reports reliability statistics over the sampled population.

Units follow the same SI conventions as the rest of the package:
    load      [N]
    length    [m]
    d_mm      [mm]  (converted internally to metres)
    stress    [Pa]
    deflection [m]
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .materials import MATERIALS
from . import beam
from .optimizer import _section_config


# ---------------------------------------------------------------------------
# Result container
# ---------------------------------------------------------------------------

@dataclass
class MonteCarloResult:
    """Statistics from a Monte Carlo reliability run."""

    n_samples: int
    fos_mean: float
    fos_std: float
    fos_p5: float            # 5th percentile of FoS
    fos_p95: float           # 95th percentile of FoS
    failure_probability: float  # fraction of samples where fos < fos_target
    deflection_mean: float
    deflection_std: float
    stress_mean: float
    stress_std: float
    samples: dict            # {"fos": ndarray, "stress": ndarray, "deflection": ndarray}


# ---------------------------------------------------------------------------
# Core simulation
# ---------------------------------------------------------------------------

def run_monte_carlo(
    material_key: str,
    section_type: str,
    d_mm: float,
    load: float,
    length: float,
    load_case: str,
    fos_target: float = 2.0,
    n_samples: int = 1000,
    load_cov: float = 0.10,
    dimension_cov: float = 0.02,
    E_cov: float = 0.05,
    sigma_y_cov: float = 0.05,
    seed: int = None,
) -> MonteCarloResult:
    """Run a Monte Carlo simulation on a single beam design.

    Each sample independently perturbs: applied load, cross-section dimension,
    Young's modulus, and yield strength — each drawn from a normal distribution
    scaled by its coefficient of variation (CoV).

    Parameters
    ----------
    material_key:
        Key into ``MATERIALS`` dict (e.g. ``"steel_a36"``).
    section_type:
        Section identifier understood by ``_section_config``
        (``"rectangle"``, ``"circle"``, ``"i_beam"``, ``"square_tube"``,
        ``"hollow_rectangle"``, ``"hollow_circle"``).
    d_mm:
        Nominal characteristic dimension in millimetres (e.g. outer diameter
        or side length).  Identical to the ``d_mm`` passed to the optimizer.
    load:
        Nominal applied load [N].
    length:
        Beam length [m].
    load_case:
        ``"cantilever_end"`` or ``"simply_center"``.
    fos_target:
        Factor-of-safety threshold below which a sample is counted as a
        failure.  Default 2.0.
    n_samples:
        Number of Monte Carlo draws.  Default 1000.
    load_cov:
        Coefficient of variation for the applied load.  Default 0.10 (10 %).
    dimension_cov:
        Coefficient of variation for the characteristic dimension.
        Default 0.02 (2 %).
    E_cov:
        Coefficient of variation for Young's modulus.  Default 0.05 (5 %).
    sigma_y_cov:
        Coefficient of variation for yield strength.  Default 0.05 (5 %).
    seed:
        Optional integer seed for the numpy random generator.  Pass ``None``
        for a non-deterministic run.

    Returns
    -------
    MonteCarloResult
        Dataclass containing summary statistics and raw sample arrays.

    Raises
    ------
    KeyError
        If ``material_key`` is not found in ``MATERIALS``.
    ValueError
        If ``load_case`` is not recognised, or if no valid samples could be
        produced (all samples had invalid geometry).
    """
    # --- validate inputs ----------------------------------------------------
    if material_key not in MATERIALS:
        raise KeyError(
            f"Unknown material key '{material_key}'. "
            f"Available: {list(MATERIALS.keys())}"
        )

    nominal_mat = MATERIALS[material_key]
    nominal_d: float = d_mm / 1000.0  # metres

    # Pre-flight check: the nominal design must itself be valid.
    if _section_config(section_type, nominal_d, d_mm) is None:
        raise ValueError(
            f"Nominal design is invalid: section_type='{section_type}', "
            f"d_mm={d_mm}"
        )

    # --- random number generator --------------------------------------------
    rng = np.random.default_rng(seed)

    # --- draw all multipliers up front (vectorised) -------------------------
    # Shape: (n_samples,) — each row is one set of perturbation multipliers.
    load_mults   = rng.normal(1.0, load_cov,      size=n_samples)
    dim_mults    = rng.normal(1.0, dimension_cov,  size=n_samples)
    E_mults      = rng.normal(1.0, E_cov,          size=n_samples)
    sigma_mults  = rng.normal(1.0, sigma_y_cov,    size=n_samples)

    # --- per-sample evaluation (loop is readable; n_samples is modest) ------
    fos_list         = []
    stress_list      = []
    deflection_list  = []

    for i in range(n_samples):
        # Perturbed scalars
        P_i  = load * load_mults[i]
        d_i  = max(nominal_d * dim_mults[i], 1e-3)  # clamp: > 1 mm
        E_i  = max(nominal_mat.E * E_mults[i], 1.0)  # clamp: > 0 (physically)
        sy_i = max(nominal_mat.sigma_y * sigma_mults[i], 1.0)  # clamp: > 0

        # Dimension label is unused in any output here; pass nominal for speed.
        cfg = _section_config(section_type, d_i, d_i * 1000.0)
        if cfg is None:
            # Perturbed dimension produced an invalid geometry — skip sample.
            continue

        sec_fn, sec_dims, _ = cfg

        try:
            props = sec_fn(*sec_dims)
        except ValueError:
            # Section guard inside section functions (e.g. wall > outer size).
            continue

        M      = beam.max_moment(P_i, length, load_case)
        sigma  = beam.max_stress(M, props)
        delta  = beam.max_deflection(P_i, length, E_i, props, load_case)
        fos    = beam.factor_of_safety(sigma, sy_i)

        fos_list.append(fos)
        stress_list.append(sigma)
        deflection_list.append(delta)

    if not fos_list:
        raise ValueError(
            "No valid samples were produced.  All perturbed geometries were "
            "invalid.  Try a larger nominal dimension or a different section type."
        )

    fos_arr   = np.array(fos_list,        dtype=float)
    stress_arr = np.array(stress_list,     dtype=float)
    defl_arr  = np.array(deflection_list,  dtype=float)

    return MonteCarloResult(
        n_samples=len(fos_arr),
        fos_mean=float(np.mean(fos_arr)),
        fos_std=float(np.std(fos_arr, ddof=1)),
        fos_p5=float(np.percentile(fos_arr, 5)),
        fos_p95=float(np.percentile(fos_arr, 95)),
        failure_probability=float(np.mean(fos_arr < fos_target)),
        deflection_mean=float(np.mean(defl_arr)),
        deflection_std=float(np.std(defl_arr, ddof=1)),
        stress_mean=float(np.mean(stress_arr)),
        stress_std=float(np.std(stress_arr, ddof=1)),
        samples={
            "fos":        fos_arr,
            "stress":     stress_arr,
            "deflection": defl_arr,
        },
    )


# ---------------------------------------------------------------------------
# Human-readable summary
# ---------------------------------------------------------------------------

def reliability_summary(result: MonteCarloResult) -> str:
    """Return a concise, human-readable summary of a MonteCarloResult.

    Example output::

        Monte Carlo (1000 samples): FoS = 2.25 ± 0.31, P(fail) = 3.2%
        5th–95th percentile FoS: [1.71, 2.82]

    Parameters
    ----------
    result:
        A ``MonteCarloResult`` returned by ``run_monte_carlo``.

    Returns
    -------
    str
        Two-line summary string.
    """
    p_fail_pct = result.failure_probability * 100.0
    line1 = (
        f"Monte Carlo ({result.n_samples} samples): "
        f"FoS = {result.fos_mean:.2f} \u00b1 {result.fos_std:.2f}, "
        f"P(fail) = {p_fail_pct:.1f}%"
    )
    line2 = (
        f"5th\u201395th percentile FoS: "
        f"[{result.fos_p5:.2f}, {result.fos_p95:.2f}]"
    )
    return f"{line1}\n{line2}"
