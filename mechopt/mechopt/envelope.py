"""Load-case envelope analysis.

Evaluate a single design under multiple load cases simultaneously and identify
the governing (worst-case) load case for each failure mode.
"""

from dataclasses import dataclass
from typing import List

import pandas as pd

from . import beam, sections
from .failure_modes import evaluate_candidate, SafetyCase, Status
from .materials import MATERIALS
from .optimizer import _section_config


@dataclass(frozen=True)
class EnvelopeCase:
    load_case: str
    load: float
    length: float
    stress: float
    deflection: float
    fos: float


@dataclass(frozen=True)
class EnvelopeResult:
    cases: List[EnvelopeCase]
    governing_case: str       # load_case string of worst case
    governing_fos: float
    governing_stress: float
    governing_deflection: float
    all_safe: bool            # True if all cases pass fos_target
    summary: str


def evaluate_envelope(
    material_key: str,
    section_type: str,
    d_mm: float,
    load_cases: list,
    fos_target: float = 2.0,
    deflection_limit: float = None,
) -> EnvelopeResult:
    """Evaluate one design under multiple load cases.

    Parameters
    ----------
    material_key : str
        Key into MATERIALS dict.
    section_type : str
        Section type name (e.g. "rectangle", "circle").
    d_mm : float
        Primary dimension in mm.
    load_cases : list of dict
        Each dict has: {"name": str, "load": float, "length": float,
                        "load_case": str}
        where load_case is "cantilever_end" or "simply_center".
    fos_target : float
        Required factor of safety.
    deflection_limit : float or None
        Maximum allowable deflection [m].

    Returns
    -------
    EnvelopeResult
    """
    mat = MATERIALS[material_key]
    d = d_mm / 1000.0

    config = _section_config(section_type, d, d_mm)
    if config is None:
        raise ValueError(
            f"Invalid geometry for {section_type} at d={d_mm}mm"
        )
    sec_fn, sec_dims, dims_str = config
    props = sec_fn(*sec_dims)

    cases = []
    for lc in load_cases:
        P = lc["load"]
        L = lc["length"]
        case_type = lc["load_case"]
        name = lc.get("name", case_type)

        M = beam.max_moment(P, L, case_type)
        sigma = beam.max_stress(M, props)
        delta = beam.max_deflection(P, L, mat.E, props, case_type)
        fos = beam.factor_of_safety(sigma, mat.sigma_y)

        cases.append(EnvelopeCase(
            load_case=name,
            load=P,
            length=L,
            stress=sigma,
            deflection=delta,
            fos=fos,
        ))

    # Find governing case (minimum FoS)
    governing = min(cases, key=lambda c: c.fos)

    # Check deflection limit across all cases
    all_safe = all(c.fos >= fos_target for c in cases)
    if deflection_limit is not None:
        all_safe = all_safe and all(
            c.deflection <= deflection_limit for c in cases
        )

    # Find worst deflection
    worst_defl = max(cases, key=lambda c: c.deflection)

    summary = (
        f"Governing: {governing.load_case} "
        f"(FoS {governing.fos:.2f}, "
        f"\u03c3 {governing.stress/1e6:.1f} MPa, "
        f"\u03b4 {worst_defl.deflection*1e3:.2f} mm)"
    )

    return EnvelopeResult(
        cases=cases,
        governing_case=governing.load_case,
        governing_fos=governing.fos,
        governing_stress=governing.stress,
        governing_deflection=worst_defl.deflection,
        all_safe=all_safe,
        summary=summary,
    )
