"""Wall-mounted bracket analysis with gusset variants and real bolt model.

Assumes a cantilevered rectangular plate/arm with a point load at offset e
from the wall, fastened with a bolt group. Gusset variants stiffen the bracket
by shortening the effective cantilever span.

Bolt model checks: shear, tension (moment), bearing, tear-out, and combined
utilization. Explicit disclaimer for wall anchorage.

Limitations: no welds, fatigue, stress concentrations, prying action, or
detailed FEA. Does NOT check wall anchorage — the wall/substrate must be
verified separately.
"""

import math
from dataclasses import dataclass, field
from typing import List, Tuple

from .sections import SectionProps, rectangle
from .materials import Material, MATERIALS


# ── Gusset types ────────────────────────────────────────────────────────────

GUSSET_TYPES = ["none", "flat_L", "triangular", "double_gusset", "ribbed"]


@dataclass(frozen=True)
class GussetSpec:
    gusset_type: str    # one of GUSSET_TYPES
    depth: float        # gusset depth along arm from wall [m] (0 for "none")
    thickness: float    # gusset plate thickness [m]
    mass: float         # added mass [kg]

    @property
    def label(self) -> str:
        return self.gusset_type.replace("_", " ").title()


def gusset_mass(gusset_type: str, depth: float, thickness: float,
                rho: float, width: float) -> float:
    """Compute added mass of a gusset [kg].

    - flat_L: rectangular stiffener, area = depth * width
    - triangular: right triangle, area = 0.5 * depth * depth
    - double_gusset: two triangular gussets (one each side)
    - ribbed: like triangular but 1.5x mass for extra rib material
    - none: 0
    """
    if gusset_type == "none" or depth <= 0:
        return 0.0
    if gusset_type == "flat_L":
        area = depth * width
    elif gusset_type == "triangular":
        area = 0.5 * depth * depth
    elif gusset_type == "double_gusset":
        area = 2 * 0.5 * depth * depth
    elif gusset_type == "ribbed":
        area = 1.5 * 0.5 * depth * depth
    else:
        area = 0.0
    return area * thickness * rho


def effective_span(e: float, gusset_type: str, gusset_depth: float) -> float:
    """Effective cantilever span after gusset stiffening.

    The gusset shortens the unsupported length. The effective span is
    clamped to a minimum of 0.01*e to avoid degenerate zero-length beams.
    """
    if gusset_type == "none" or gusset_depth <= 0:
        return e
    e_eff = max(e - gusset_depth, 0.01 * e)
    return e_eff


def make_gusset(gusset_type: str, depth: float, thickness: float,
                rho: float, width: float) -> GussetSpec:
    """Create a GussetSpec with computed mass."""
    mass = gusset_mass(gusset_type, depth, thickness, rho, width)
    return GussetSpec(
        gusset_type=gusset_type,
        depth=depth if gusset_type != "none" else 0.0,
        thickness=thickness,
        mass=mass,
    )


# ── Bolt model (real) ──────────────────────────────────────────────────────

@dataclass(frozen=True)
class BoltResult:
    shear_per_bolt: float       # N
    max_tension: float          # N
    bolt_area: float            # m^2
    shear_stress: float         # Pa
    tension_stress: float       # Pa
    combined_utilization: float # dimensionless (<=1 is OK)
    bolt_fos: float             # dimensionless
    bearing_stress: float       # Pa
    bearing_fos: float          # dimensionless
    tearout_stress: float       # Pa
    tearout_fos: float          # dimensionless
    edge_distance_ok: bool      # True if edge dist >= 1.5 * d_bolt
    warnings: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class BracketResult:
    plate_stress: float         # Pa
    plate_deflection: float     # m
    plate_fos: float
    bolt: BoltResult
    overall_fos: float
    safe: bool
    controlling: str            # "plate_bending" | "bolt" | "deflection" |
                                # "bearing" | "tearout"
    gusset: GussetSpec = None
    plate_mass: float = 0.0     # plate mass [kg]
    total_mass: float = 0.0     # plate + gusset mass [kg]


# ── Plate helpers ───────────────────────────────────────────────────────────

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


# ── Bolt calculations ──────────────────────────────────────────────────────

def bearing_stress(P: float, n_bolts: int, bolt_dia: float,
                   plate_thickness: float) -> float:
    """Bearing stress on the plate at bolt holes [Pa].

    sigma_br = P / (n * d_bolt * t_plate)
    """
    return P / (n_bolts * bolt_dia * plate_thickness)


def tearout_stress(P: float, n_bolts: int, bolt_dia: float,
                   plate_thickness: float, edge_distance: float,
                   hole_clearance: float = 0.0015) -> float:
    """Tear-out shear stress [Pa].

    tau = P / (n * 2 * L_shear * t)
    where L_shear = edge_distance - d_hole/2
    and d_hole = d_bolt + hole_clearance
    """
    d_hole = bolt_dia + hole_clearance
    L_shear = edge_distance - d_hole / 2
    if L_shear <= 0:
        return float("inf")
    return P / (n_bolts * 2 * L_shear * plate_thickness)


def bolt_group_loads(P: float, moment: float,
                     bolt_positions: List[Tuple[float, float]]) -> BoltResult:
    """Compute bolt shear, tension, and combined utilization.

    Retained for API compatibility — prefer evaluate_bracket() instead.
    """
    raise NotImplementedError("Use evaluate_bracket() instead")


# ── Main evaluation ────────────────────────────────────────────────────────

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
    gusset_type: str = "none",
    gusset_depth: float = 0.0,
    gusset_thickness: float = None,
    edge_distance: float = None,
) -> BracketResult:
    """Full bracket evaluation: plate bending + bolt group + gusset + bearing/tearout.

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
    gusset_type : one of GUSSET_TYPES (default "none")
    gusset_depth : gusset depth along arm [m] (default 0)
    gusset_thickness : gusset plate thickness [m] (default = plate thickness)
    edge_distance : bolt edge distance [m] (default = 2 * bolt_diameter)

    Note: does NOT check wall anchorage — verify substrate separately.
    """
    if gusset_thickness is None:
        gusset_thickness = thickness
    if edge_distance is None:
        edge_distance = 2 * bolt_diameter

    # --- Gusset ---
    gusset = make_gusset(gusset_type, gusset_depth, gusset_thickness,
                         mat.rho, width)
    e_eff = effective_span(e, gusset_type, gusset_depth)

    # --- Plate ---
    M = P * e_eff
    props = rectangular_plate_props(width, thickness)
    stress = M * props.c / props.I
    deflection = P * e_eff**3 / (3 * mat.E * props.I)
    p_fos = plate_factor_of_safety(stress, mat.sigma_y)

    plate_mass = width * e * thickness * mat.rho
    total_mass = plate_mass + gusset.mass

    # --- Bolt group: shear + tension ---
    n = max(bolt_count, 1)
    bolt_area = math.pi * bolt_diameter**2 / 4

    shear_per_bolt = P / n

    positions_y = []
    for i in range(n):
        y = (i - (n - 1) / 2) * bolt_spacing_v
        positions_y.append(y)

    sum_r2 = sum(y**2 for y in positions_y)
    if sum_r2 > 0:
        max_r = max(abs(y) for y in positions_y)
        max_tension = M * max_r / sum_r2
    else:
        max_tension = M / max(bolt_diameter, 1e-6)

    shear_stress_val = shear_per_bolt / bolt_area
    tension_stress_val = max_tension / bolt_area

    combined_stress = math.sqrt(shear_stress_val**2 + tension_stress_val**2)
    combined_utilization = combined_stress / bolt_sigma_allow
    bolt_fos = bolt_sigma_allow / combined_stress if combined_stress > 0 else float("inf")

    # --- Bolt: bearing ---
    br_stress = bearing_stress(P, n, bolt_diameter, thickness)
    bearing_allow = 1.5 * mat.sigma_y  # AISC bearing allowable
    br_fos = bearing_allow / br_stress if br_stress > 0 else float("inf")

    # --- Bolt: tear-out ---
    to_stress = tearout_stress(P, n, bolt_diameter, thickness, edge_distance)
    shear_allow = 0.6 * mat.sigma_y  # shear yield allowable
    to_fos = shear_allow / to_stress if to_stress > 0 else float("inf")

    # --- Edge distance check ---
    edge_ok = edge_distance >= 1.5 * bolt_diameter

    # --- Warnings ---
    warnings = []
    if not edge_ok:
        warnings.append(
            f"Edge distance {edge_distance*1000:.1f} mm < 1.5d = "
            f"{1.5*bolt_diameter*1000:.1f} mm — risk of tear-out"
        )
    warnings.append("Does not check wall anchorage — verify substrate separately")

    bolt_result = BoltResult(
        shear_per_bolt=shear_per_bolt,
        max_tension=max_tension,
        bolt_area=bolt_area,
        shear_stress=shear_stress_val,
        tension_stress=tension_stress_val,
        combined_utilization=combined_utilization,
        bolt_fos=bolt_fos,
        bearing_stress=br_stress,
        bearing_fos=br_fos,
        tearout_stress=to_stress,
        tearout_fos=to_fos,
        edge_distance_ok=edge_ok,
        warnings=warnings,
    )

    # --- Overall ---
    all_fos = [p_fos, bolt_fos, br_fos, to_fos]
    overall_fos = min(all_fos)

    # Determine controlling constraint
    fos_map = {
        "plate_bending": p_fos,
        "bolt": bolt_fos,
        "bearing": br_fos,
        "tearout": to_fos,
    }
    controlling = min(fos_map, key=fos_map.get)
    safe = overall_fos >= fos_target

    if deflection_limit is not None and deflection > deflection_limit:
        controlling = "deflection"
        safe = False

    return BracketResult(
        plate_stress=stress,
        plate_deflection=deflection,
        plate_fos=p_fos,
        bolt=bolt_result,
        overall_fos=overall_fos,
        safe=safe,
        controlling=controlling,
        gusset=gusset,
        plate_mass=plate_mass,
        total_mass=total_mass,
    )


def compare_gussets(
    P: float, e: float, width: float, thickness: float,
    mat: Material, fos_target: float,
    bolt_count: int, bolt_diameter: float, bolt_spacing_v: float,
    bolt_sigma_allow: float = 640e6,
    deflection_limit: float = None,
    gusset_depth: float = 0.05,
    gusset_thickness: float = None,
    edge_distance: float = None,
) -> List[BracketResult]:
    """Evaluate all gusset variants and return results for comparison."""
    results = []
    for gt in GUSSET_TYPES:
        result = evaluate_bracket(
            P=P, e=e, width=width, thickness=thickness,
            mat=mat, fos_target=fos_target,
            bolt_count=bolt_count, bolt_diameter=bolt_diameter,
            bolt_spacing_v=bolt_spacing_v, bolt_sigma_allow=bolt_sigma_allow,
            deflection_limit=deflection_limit,
            gusset_type=gt,
            gusset_depth=gusset_depth,
            gusset_thickness=gusset_thickness,
            edge_distance=edge_distance,
        )
        results.append(result)
    return results
