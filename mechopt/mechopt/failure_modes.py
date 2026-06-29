"""Failure-mode screening: evaluate a beam candidate against multiple checks.

Runs bending stress, deflection, yield FoS, Euler buckling, shear,
torsion (when torque given), and local buckling checks, then rolls up
results into a SafetyCase with an overall pass / fail / warning verdict.
"""

from dataclasses import dataclass
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
                       compression_load=None, K=1.0,
                       section_type=None, dims_dict=None,
                       torque=None) -> SafetyCase:
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
        "cantilever_end", "cantilever_udl", "simply_center", or "simply_udl".
    fos_target : float
        Required factor of safety against yield (default 1.5).
    deflection_limit : float or None
        Maximum allowable deflection [m], or None to skip.
    compression_load : float or None
        Axial compression load [N] for buckling check, or None to skip.
    K : float
        Effective-length factor for buckling (default 1.0).
    section_type : str or None
        Section type name (e.g. "rectangle", "square_tube").  Required for
        the local-buckling check; pass None to skip that check.
    dims_dict : dict or None
        Dimension dictionary for local-buckling slenderness calculation.
        Required when section_type is a thin-walled type; None to skip.

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

    # -- shear --
    V = beam.max_shear(load, load_case)
    _st = section_type if section_type is not None else "rectangle"
    tau_max = beam.max_shear_stress(V, props.A, _st)
    tau_allow = 0.6 * material.sigma_y
    s_fos = beam.shear_fos(tau_max, material.sigma_y)
    margin_shear = (s_fos - fos_target) / fos_target
    checks.append(CheckResult(
        name="shear",
        actual=s_fos,
        allowable=fos_target,
        margin=margin_shear,
        status=_status_from_margin(margin_shear),
        notes=f"\u03c4={tau_max/1e6:.1f} MPa, FoS_shear={s_fos:.2f}",
    ))

    # -- torsion (requires torque input) --
    if torque is not None and torque > 0:
        # Simplified torsion: τ = T·c / J
        # For circular sections, J = 2I; for others, approximate J ≈ I
        if _st == "circle" or _st == "hollow_circle":
            J = 2 * props.I
        else:
            J = props.I  # conservative approximation for non-circular
        tau_torsion = torque * props.c / J
        torsion_fos = tau_allow / tau_torsion
        margin_tor = (torsion_fos - fos_target) / fos_target
        checks.append(CheckResult(
            name="torsion",
            actual=torsion_fos,
            allowable=fos_target,
            margin=margin_tor,
            status=_status_from_margin(margin_tor),
            notes=f"\u03c4_t={tau_torsion/1e6:.1f} MPa, FoS_torsion={torsion_fos:.2f}",
        ))
    else:
        checks.append(CheckResult(
            name="torsion",
            actual=0.0,
            allowable=0.0,
            margin=0.0,
            status=Status.NOT_MODELED,
            notes="No torque applied",
        ))

    # -- local_buckling (thin-walled sections only) --
    if section_type is not None:
        ok = beam.local_buckling_ok(
            section_type,
            dims_dict if dims_dict is not None else {},
            material.E,
            material.sigma_y,
        )
        if ok is None:
            # Solid section — no local buckling risk
            checks.append(CheckResult(
                name="local_buckling",
                actual=0.0,
                allowable=0.0,
                margin=0.0,
                status=Status.NOT_MODELED,
                notes="N/A (solid section)",
            ))
        else:
            lam = beam.local_buckling_slenderness(section_type,
                                                   dims_dict if dims_dict is not None else {})
            limit = beam.local_buckling_limit(section_type, material.E, material.sigma_y)
            if ok:
                margin_lb = (limit - lam) / limit
                lb_status = _status_from_margin(margin_lb)
            else:
                margin_lb = (limit - lam) / limit  # negative when lam > limit
                lb_status = Status.FAIL
            checks.append(CheckResult(
                name="local_buckling",
                actual=lam,
                allowable=limit,
                margin=margin_lb,
                status=lb_status,
                notes=f"slenderness={lam:.2f}, limit={limit:.2f}",
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
