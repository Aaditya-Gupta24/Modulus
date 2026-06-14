"""Simplified wall-mounted bracket analysis.

Assumes a cantilevered rectangular plate/arm with a point load at offset e
from the wall, fastened with a bolt group.

Limitations: no welds, fatigue, stress concentrations, local tear-out,
bearing failure, prying action, buckling, or detailed FEA.
"""

import math
from dataclasses import dataclass
from typing import List, Tuple

from .sections import SectionProps, rectangle
from .materials import Material, MATERIALS


@dataclass(frozen=True)
class BoltResult:
    shear_per_bolt: float       # N
    max_tension: float          # N
    bolt_area: float            # m^2
    shear_stress: float         # Pa
    tension_stress: float       # Pa
    combined_utilization: float # dimensionless (<=1 is OK)
    bolt_fos: float             # dimensionless


@dataclass(frozen=True)
class BracketResult:
    plate_stress: float         # Pa
    plate_deflection: float     # m
    plate_fos: float
    bolt: BoltResult
    overall_fos: float
    safe: bool
    controlling: str            # "plate_bending" | "bolt" | "deflection"


def rectangular_plate_props(width: float, thickness: float) -> SectionProps:
    """Section properties for a rectangular plate bending about the weak axis."""
    return rectangle(width, thickness)


def bracket_plate_stress(P: float, e: float, width: float,
                         thickness: float) -> float:
    """Maximum bending stress in the plate [Pa].  sigma = M*c/I"""
    M = P * e
    props = rectangular_plate_props(width, thickness)
    return M * props.c / props.I


def bracket_plate_deflection(P: float, e: float, E: float, width: float,
                             thickness: float) -> float:
    """Tip deflection of a cantilevered plate [m].  delta = P*e^3 / (3*E*I)"""
    props = rectangular_plate_props(width, thickness)
    return P * e**3 / (3 * E * props.I)


def plate_factor_of_safety(stress: float, sigma_y: float) -> float:
    """FoS = sigma_y / stress"""
    if stress == 0:
        return float("inf")
    return sigma_y / stress


def bolt_group_loads(P: float, moment: float,
                     bolt_positions: List[Tuple[float, float]]) -> BoltResult:
    """Compute bolt shear, tension, and combined utilization.

    bolt_positions: list of (x, y) in metres from the bolt-group centroid.
    Bolt material assumed to be Grade 8.8 (640 MPa proof, ~800 MPa tensile).
    Bolt area computed from the first bolt's radial distance metadata —
    caller must also supply bolt_diameter separately; here we use a default.

    For this simplified model:
      - Direct shear: V = P / n  (equally shared)
      - Moment tension: T_i = M * r_i / sum(r_j^2)
      - Combined utilization: sqrt((V/A)^2 + (T_max/A)^2) / sigma_allow
    """
    raise NotImplementedError("Use evaluate_bracket() instead")


def evaluate_bracket(
    P: float,
    e: float,
    width: float,
    thickness: float,
    mat: Material,
    fos_target: float,
    bolt_count: int,
    bolt_diameter: float,
    bolt_spacing_v: float,
    bolt_sigma_allow: float = 640e6,
    deflection_limit: float = None,
) -> BracketResult:
    """Full bracket evaluation: plate bending + bolt group.

    Parameters
    ----------
    P : load [N]
    e : load offset from wall [m]
    width : plate width [m]
    thickness : plate thickness [m]
    mat : plate material
    fos_target : minimum required factor of safety
    bolt_count : number of bolts
    bolt_diameter : bolt shank diameter [m]
    bolt_spacing_v : vertical spacing between bolts [m]
    bolt_sigma_allow : bolt allowable stress [Pa] (default Grade 8.8 proof)
    deflection_limit : max allowable deflection [m] or None
    """
    # --- Plate ---
    M = P * e
    props = rectangular_plate_props(width, thickness)
    stress = M * props.c / props.I
    deflection = P * e**3 / (3 * mat.E * props.I)
    p_fos = plate_factor_of_safety(stress, mat.sigma_y)

    # --- Bolt group ---
    n = max(bolt_count, 1)
    bolt_area = math.pi * bolt_diameter**2 / 4

    # Direct shear equally distributed
    shear_per_bolt = P / n

    # Bolt positions relative to centroid (vertical line of bolts)
    positions_y = []
    for i in range(n):
        y = (i - (n - 1) / 2) * bolt_spacing_v
        positions_y.append(y)

    sum_r2 = sum(y**2 for y in positions_y)
    if sum_r2 > 0:
        max_r = max(abs(y) for y in positions_y)
        max_tension = M * max_r / sum_r2
    else:
        # Single bolt at centroid — all moment goes to one bolt
        max_tension = M / max(bolt_diameter, 1e-6)  # conservative fallback

    shear_stress = shear_per_bolt / bolt_area
    tension_stress = max_tension / bolt_area

    combined_stress = math.sqrt(shear_stress**2 + tension_stress**2)
    combined_utilization = combined_stress / bolt_sigma_allow
    bolt_fos = bolt_sigma_allow / combined_stress if combined_stress > 0 else float("inf")

    # --- Overall ---
    overall_fos = min(p_fos, bolt_fos)

    # Determine controlling constraint
    if deflection_limit is not None and deflection > deflection_limit:
        controlling = "deflection"
        safe = False
    elif p_fos < bolt_fos:
        controlling = "plate_bending"
        safe = overall_fos >= fos_target
    else:
        controlling = "bolt"
        safe = overall_fos >= fos_target

    # Even if controlling is not deflection, still check fos
    if controlling != "deflection":
        safe = overall_fos >= fos_target
    # If deflection controls, also check fos
    if deflection_limit is not None and deflection > deflection_limit:
        safe = False

    bolt_result = BoltResult(
        shear_per_bolt=shear_per_bolt,
        max_tension=max_tension,
        bolt_area=bolt_area,
        shear_stress=shear_stress,
        tension_stress=tension_stress,
        combined_utilization=combined_utilization,
        bolt_fos=bolt_fos,
    )

    return BracketResult(
        plate_stress=stress,
        plate_deflection=deflection,
        plate_fos=p_fos,
        bolt=bolt_result,
        overall_fos=overall_fos,
        safe=safe,
        controlling=controlling,
    )
