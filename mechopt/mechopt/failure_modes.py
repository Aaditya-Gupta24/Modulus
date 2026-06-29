"""Failure-mode screening: evaluate a beam candidate against multiple checks.

Runs bending stress, deflection, yield FoS, Euler buckling, and placeholder
shear / torsion checks, then rolls up results into a SafetyCase with an
overall pass / fail / warning verdict.
"""

from dataclasses import dataclass, field
from typing import List
from enum import Enum

from . import beam, buckling


class Status(Enum):
    PASS = "pass"
    FAIL = "fail"
    WARNING = "warning"
    NOT_MODELED = "not_modeled"


@dataclass(frozen=True)
class CheckResult:
    name: str
    actual: float
    allowable: float
    margin: float
    status: Status
    notes: str = ""


@dataclass
class SafetyCase:
    checks: List[CheckResult]
    overall_status: Status
    controlling_check: str
    failure_reasons: List[str]


def _status_from_margin(margin: float) -> Status:
    """Return FAIL / WARNING / PASS based on margin value."""
    if margin < 0:
        return Status.FAIL
    if margin < 0.10:
        return Status.WARNING
    return Status.PASS


def evaluate_candidate(material, section_fn, dims, load, length, load_case,
                       fos_target=1.5, deflection_limit=None,
                       compression_load=None, K=1.0) -> SafetyCase:
    """Evaluate a beam candidate against all failure-mode checks.

    Parameters
    ----------
    material : Material
        Material dataclass (E, sigma_y, rho, cost).
    section_fn : callable
        Section geometry function (e.g. sections.rectangle).
    dims : tuple
        Arguments to pass to section_fn.
    load : float
        Applied load [N].
    length : float
        Beam span [m].
    load_case : str
        "cantilever_end" or "simply_center".
    fos_target : float
        Required factor of safety against yield (default 1.5).
    deflection_limit : float or None
        Maximum allowable deflection [m], or None to skip.
    compression_load : float or None
        Axial compression load [N] for buckling check, or None to skip.
    K : float
        Effective-length factor for buckling (default 1.0).

    Returns
    -------
    SafetyCase
    """
    props = section_fn(*dims)
    checks: List[CheckResult] = []

    # -- bending_stress --
    M = beam.max_moment(load, length, load_case)
    sigma = beam.max_stress(M, props)
    margin_bs = (material.sigma_y - sigma) / material.sigma_y
    checks.append(CheckResult(
        name="bending_stress",
        actual=sigma,
        allowable=material.sigma_y,
        margin=margin_bs,
        status=_status_from_margin(margin_bs),
    ))

    # -- deflection (optional) --
    if deflection_limit is not None:
        delta = beam.max_deflection(load, length, material.E, props, load_case)
        margin_defl = (deflection_limit - delta) / deflection_limit
        checks.append(CheckResult(
            name="deflection",
            actual=delta,
            allowable=deflection_limit,
            margin=margin_defl,
            status=_status_from_margin(margin_defl),
        ))

    # -- yield_fos --
    fos = beam.factor_of_safety(sigma, material.sigma_y)
    margin_fos = (fos - fos_target) / fos_target
    checks.append(CheckResult(
        name="yield_fos",
        actual=fos,
        allowable=fos_target,
        margin=margin_fos,
        status=_status_from_margin(margin_fos),
    ))

    # -- euler_buckling (optional) --
    if compression_load is not None:
        P_cr = buckling.euler_critical_load(material.E, props.I, length, K)
        buckling_fos = buckling.buckling_factor_of_safety(compression_load, P_cr)
        margin_buck = (buckling_fos - 1.0) / 1.0
        checks.append(CheckResult(
            name="euler_buckling",
            actual=buckling_fos,
            allowable=1.0,
            margin=margin_buck,
            status=_status_from_margin(margin_buck),
        ))

    # -- shear (not modeled) --
    checks.append(CheckResult(
        name="shear",
        actual=0.0,
        allowable=0.0,
        margin=0.0,
        status=Status.NOT_MODELED,
        notes="Shear check not yet implemented",
    ))

    # -- torsion (not modeled) --
    checks.append(CheckResult(
        name="torsion",
        actual=0.0,
        allowable=0.0,
        margin=0.0,
        status=Status.NOT_MODELED,
        notes="Torsion check not yet implemented",
    ))

    # -- roll up --
    modeled = [c for c in checks if c.status is not Status.NOT_MODELED]

    if any(c.status is Status.FAIL for c in modeled):
        overall = Status.FAIL
    elif any(c.status is Status.WARNING for c in modeled):
        overall = Status.WARNING
    else:
        overall = Status.PASS

    controlling = min(modeled, key=lambda c: c.margin).name
    failure_reasons = [c.name for c in modeled if c.status is Status.FAIL]

    return SafetyCase(
        checks=checks,
        overall_status=overall,
        controlling_check=controlling,
        failure_reasons=failure_reasons,
    )
