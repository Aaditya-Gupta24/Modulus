"""Euler column buckling — elastic critical load for slender compression members.

A bending screen is not enough for members loaded in compression: a slender
column can fail by buckling at a load well below its yield strength. This module
adds the classical Euler check.

    P_cr = pi**2 * E * I / (K * L)**2          (elastic critical / Euler load)
    r    = sqrt(I / A)                          (radius of gyration)
    lambda = K * L / r                          (slenderness ratio)
    buckling FoS = P_cr / P_applied

K is the effective-length factor for the end conditions:
    pinned-pinned        K = 1.0
    fixed-free (cantilever column)  K = 2.0
    fixed-fixed          K = 0.5
    fixed-pinned         K ~= 0.7

Limitations: this is *elastic* (Euler) buckling only. It is unconservative for
stocky columns (low slenderness), where inelastic/Johnson behaviour governs, and
it does not model local/wall buckling of thin tubes. Use as a screening check.
"""

import math

from .sections import SectionProps


def euler_critical_load(E: float, I: float, L: float, K: float = 1.0) -> float:
    """Elastic critical (Euler) buckling load [N].  P_cr = pi^2 E I / (K L)^2."""
    if E <= 0 or I <= 0 or L <= 0 or K <= 0:
        raise ValueError("E, I, L, and K must all be positive.")
    return math.pi**2 * E * I / (K * L) ** 2


def radius_of_gyration(props: SectionProps) -> float:
    """Radius of gyration [m].  r = sqrt(I / A)."""
    return math.sqrt(props.I / props.A)


def slenderness_ratio(L: float, props: SectionProps, K: float = 1.0) -> float:
    """Slenderness ratio (dimensionless).  lambda = K L / r."""
    return K * L / radius_of_gyration(props)


def buckling_factor_of_safety(P_applied: float, P_cr: float) -> float:
    """Factor of safety against buckling.  FoS = P_cr / P_applied."""
    if P_applied <= 0:
        raise ValueError("Applied compressive load must be positive.")
    return P_cr / P_applied
