"""Beam mechanics: bending stress, deflection, factor of safety.

Four load cases are supported, selected by a string:
    "cantilever_end"      : cantilever, point load P at the free end.
    "cantilever_udl"      : cantilever, uniformly distributed load (P = total load).
    "simply_center"       : simply supported, point load P at mid-span.
    "simply_udl"          : simply supported, uniformly distributed load (P = total load).

Assumptions (document in README): linear-elastic, small deflection, static
load, prismatic beam, no buckling / stress-concentration / fatigue effects.

IMPLEMENT THESE. Signatures and units are fixed by the tests.
"""

from .sections import SectionProps


def max_moment(P: float, L: float, load_case: str) -> float:
    """Maximum bending moment [N*m].

    cantilever_end : M = P*L
    cantilever_udl : M = P*L/2  (P is total distributed load)
    simply_center  : M = P*L/4
    simply_udl     : M = P*L/8  (P is total distributed load)
    """
    if load_case == "cantilever_end":
        return P * L
    elif load_case == "cantilever_udl":
        return P * L / 2
    elif load_case == "simply_center":
        return P * L / 4
    elif load_case == "simply_udl":
        return P * L / 8
    else:
        raise ValueError(
            f"Unknown load_case: {load_case!r}. "
            "Valid options: 'cantilever_end', 'cantilever_udl', "
            "'simply_center', 'simply_udl'."
        )


def max_stress(M: float, props: SectionProps) -> float:
    """Maximum bending stress [Pa].  sigma = M*c/I"""
    return M * props.c / props.I


def max_deflection(P: float, L: float, E: float, props: SectionProps,
                   load_case: str) -> float:
    """Maximum deflection [m].

    cantilever_end : delta = P*L**3 / (3*E*I)
    cantilever_udl : delta = P*L**3 / (8*E*I)   (P is total distributed load)
    simply_center  : delta = P*L**3 / (48*E*I)
    simply_udl     : delta = 5*P*L**3 / (384*E*I) (P is total distributed load)
    """
    if load_case == "cantilever_end":
        return P * L**3 / (3 * E * props.I)
    elif load_case == "cantilever_udl":
        return P * L**3 / (8 * E * props.I)
    elif load_case == "simply_center":
        return P * L**3 / (48 * E * props.I)
    elif load_case == "simply_udl":
        return 5 * P * L**3 / (384 * E * props.I)
    else:
        raise ValueError(
            f"Unknown load_case: {load_case!r}. "
            "Valid options: 'cantilever_end', 'cantilever_udl', "
            "'simply_center', 'simply_udl'."
        )


def factor_of_safety(sigma: float, sigma_y: float) -> float:
    """FoS = sigma_y / sigma  (against yield)."""
    return sigma_y / sigma


def max_shear(P: float, load_case: str) -> float:
    """Maximum transverse shear force [N].

    cantilever_end / cantilever_udl : V = P
    simply_center  / simply_udl     : V = P / 2
    """
    if load_case in ("cantilever_end", "cantilever_udl"):
        return P
    elif load_case in ("simply_center", "simply_udl"):
        return P / 2
    else:
        raise ValueError(
            f"Unknown load_case: {load_case!r}. "
            "Valid options: 'cantilever_end', 'cantilever_udl', "
            "'simply_center', 'simply_udl'."
        )


def shear_shape_factor(section_type: str) -> float:
    """Return the transverse shear shape factor k for max shear stress tau = k*V/A.

    rectangle : k = 1.5  (exact for solid rectangle)
    circle    : k = 4/3  (exact for solid circle)
    all other : k = 1.5  (conservative approximation for I-beams, tubes, etc.)
    """
    if section_type == "rectangle":
        return 1.5
    elif section_type == "circle":
        return 4.0 / 3.0
    else:
        # For I-beams, tubes, hollow sections: approximate as 1.5 (conservative)
        return 1.5


def max_shear_stress(V: float, A: float, section_type: str) -> float:
    """Maximum transverse shear stress [Pa].  tau = k*V/A."""
    k = shear_shape_factor(section_type)
    return k * V / A


def shear_fos(tau_max: float, sigma_y: float) -> float:
    """Shear factor of safety.  tau_allow = 0.6*sigma_y (von Mises criterion)."""
    tau_allow = 0.6 * sigma_y
    return tau_allow / tau_max


def local_buckling_slenderness(section_type: str, dims_dict: dict) -> float | None:
    """Return the plate slenderness ratio for thin-walled sections, or None if solid.

    square_tube      : (a - 2*w) / w   (flat-wall slenderness)
    hollow_rectangle : max((b - 2*w)/w, (h - 2*w)/w)  (worst face)
    hollow_circle    : d / t            (D/t ratio; t = wall thickness)
    i_beam           : (b/2) / tf       (half-flange outstand / flange thickness)
    solid sections   : None
    """
    if section_type == "square_tube":
        a, w = dims_dict["a"], dims_dict["w"]
        return (a - 2 * w) / w
    elif section_type == "hollow_rectangle":
        b, h, w = dims_dict["b"], dims_dict["h"], dims_dict["w"]
        return max((b - 2 * w) / w, (h - 2 * w) / w)
    elif section_type == "hollow_circle":
        d, t = dims_dict["d"], dims_dict["t"]
        return d / t
    elif section_type == "i_beam":
        b, tf = dims_dict["b"], dims_dict["tf"]
        return (b / 2) / tf
    else:
        return None  # solid sections don't have local buckling


def local_buckling_limit(section_type: str, E: float, sigma_y: float) -> float | None:
    """Return the compact-section slenderness limit (AISC basis), or None if solid.

    square_tube / hollow_rectangle / i_beam : 1.12 * sqrt(E / sigma_y)
    hollow_circle                           : 0.07 * E / sigma_y
    solid sections                          : None
    """
    if section_type in ("square_tube", "hollow_rectangle", "i_beam"):
        return 1.12 * (E / sigma_y) ** 0.5
    elif section_type == "hollow_circle":
        return 0.07 * E / sigma_y
    else:
        return None


def local_buckling_ok(section_type: str, dims_dict: dict,
                      E: float, sigma_y: float) -> bool | None:
    """Check if section is compact (no local buckling risk).

    Returns True if the slenderness is within the compact-section limit,
    False if it exceeds the limit, or None for solid sections.
    """
    lam = local_buckling_slenderness(section_type, dims_dict)
    if lam is None:
        return None
    limit = local_buckling_limit(section_type, E, sigma_y)
    return lam <= limit
