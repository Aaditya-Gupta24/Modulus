"""Beam mechanics: bending stress, deflection, factor of safety.

Two load cases are supported, selected by a string:
    "cantilever_end"      : cantilever, point load P at the free end.
    "simply_center"       : simply supported, point load P at mid-span.

Assumptions (document in README): linear-elastic, small deflection, static
load, prismatic beam, no buckling / stress-concentration / fatigue effects.

IMPLEMENT THESE. Signatures and units are fixed by the tests.
"""

from .sections import SectionProps


def max_moment(P: float, L: float, load_case: str) -> float:
    """Maximum bending moment [N*m].

    cantilever_end : M = P*L
    simply_center  : M = P*L/4
    """
    if load_case == "cantilever_end":
        return P * L
    elif load_case == "simply_center":
        return P * L / 4
    else:
        raise ValueError(f"Unknown load case: {load_case}")


def max_stress(M: float, props: SectionProps) -> float:
    """Maximum bending stress [Pa].  sigma = M*c/I"""
    return M * props.c / props.I


def max_deflection(P: float, L: float, E: float, props: SectionProps,
                   load_case: str) -> float:
    """Maximum deflection [m].

    cantilever_end : delta = P*L**3 / (3*E*I)
    simply_center  : delta = P*L**3 / (48*E*I)
    """
    if load_case == "cantilever_end":
        return P * L**3 / (3 * E * props.I)
    elif load_case == "simply_center":
        return P * L**3 / (48 * E * props.I)
    else:
        raise ValueError(f"Unknown load case: {load_case}")


def factor_of_safety(sigma: float, sigma_y: float) -> float:
    """FoS = sigma_y / sigma  (against yield)."""
    return sigma_y / sigma
