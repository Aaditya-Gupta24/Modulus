"""Cross-section geometry.

Each function returns the cross-sectional area A [m^2], the second moment of
area I [m^4] about the bending (neutral) axis, and c [m], the distance from the
neutral axis to the outermost fibre.

IMPLEMENT THESE. Signatures and units are fixed by the tests — do not change
them. See SPEC.md for the equations.
"""

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
    raise NotImplementedError


def circle(d: float) -> SectionProps:
    """Solid circle, diameter d.

    A = pi*d**2/4 ;  I = pi*d**4/64 ;  c = d/2
    """
    raise NotImplementedError


def i_beam(b: float, h: float, tf: float, tw: float) -> SectionProps:
    """Symmetric I-beam: flange width b, total height h, flange thickness tf,
    web thickness tw.

    Compute I as (outer b*h rectangle) minus the two rectangular voids on each
    side of the web:  I = (b*h**3)/12 - ((b - tw)*(h - 2*tf)**3)/12.
    A = b*h - (b - tw)*(h - 2*tf) ;  c = h/2
    """
    raise NotImplementedError
