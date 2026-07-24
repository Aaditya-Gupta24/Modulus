"""Cross-section geometry.

Each function returns the cross-sectional area A [m^2], the second moment of
area I [m^4] about the bending (neutral) axis, and c [m], the distance from the
neutral axis to the outermost fibre.

IMPLEMENT THESE. Signatures and units are fixed by the tests — do not change
them. See SPEC.md for the equations.
"""

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class SectionProps:
    A: float    # area, m^2
    I: float    # second moment of area, m^4
    c: float    # neutral-axis-to-outer-fibre distance, m


def rectangle(b: float, h: float) -> SectionProps:
    """Solid rectangle, width b, height h (h is the bending direction).

    A = b*h ;  I = b*h**3 / 12 ;  c = h/2
    """
    A = b * h
    I = b * h**3 / 12
    c = h / 2
    return SectionProps(A=A, I=I, c=c)


def circle(d: float) -> SectionProps:
    """Solid circle, diameter d.

    A = pi*d**2/4 ;  I = pi*d**4/64 ;  c = d/2
    """
    A = math.pi * d**2 / 4
    I = math.pi * d**4 / 64
    c = d / 2
    return SectionProps(A=A, I=I, c=c)


def i_beam(b: float, h: float, tf: float, tw: float) -> SectionProps:
    """Symmetric I-beam: flange width b, total height h, flange thickness tf,
    web thickness tw.

    Compute I as (outer b*h rectangle) minus the two rectangular voids on each
    side of the web:  I = (b*h**3)/12 - ((b - tw)*(h - 2*tf)**3)/12.
    A = b*h - (b - tw)*(h - 2*tf) ;  c = h/2
    """
    A = b * h - (b - tw) * (h - 2 * tf)
    I = (b * h**3) / 12 - ((b - tw) * (h - 2 * tf)**3) / 12
    c = h / 2
    return SectionProps(A=A, I=I, c=c)


def hollow_rectangle(b: float, h: float, w: float) -> SectionProps:
    """Hollow rectangle (box tube), outer width b, outer height h, wall thickness w.

    bi = b - 2*w ; hi = h - 2*w
    A = b*h - bi*hi ;  I = (b*h**3 - bi*hi**3) / 12 ;  c = h/2
    """
    if w <= 0 or 2 * w >= min(b, h):
        raise ValueError(
            f"Invalid hollow rectangle: w={w} must be > 0 and 2*w < min(b={b}, h={h})"
        )
    bi = b - 2 * w
    hi = h - 2 * w
    A = b * h - bi * hi
    I = (b * h**3 - bi * hi**3) / 12
    c = h / 2
    return SectionProps(A=A, I=I, c=c)


def square_tube(a: float, w: float) -> SectionProps:
    """Square tube, outer side a, wall thickness w.

    ai = a - 2*w
    A = a**2 - ai**2 ;  I = (a**4 - ai**4) / 12 ;  c = a/2
    """
    if w <= 0 or 2 * w >= a:
        raise ValueError(
            f"Invalid square tube: w={w} must be > 0 and 2*w < a={a}"
        )
    ai = a - 2 * w
    A = a**2 - ai**2
    I = (a**4 - ai**4) / 12
    c = a / 2
    return SectionProps(A=A, I=I, c=c)


def hollow_circle(d: float, di: float) -> SectionProps:
    """Hollow circle (round tube), outer diameter d, inner diameter di.

    A = pi*(d**2 - di**2) / 4 ;  I = pi*(d**4 - di**4) / 64 ;  c = d/2
    """
    if di < 0 or di >= d:
        raise ValueError(
            f"Invalid hollow circle: di={di} must be >= 0 and < d={d}"
        )
    A = math.pi * (d**2 - di**2) / 4
    I = math.pi * (d**4 - di**4) / 64
    c = d / 2
    return SectionProps(A=A, I=I, c=c)
