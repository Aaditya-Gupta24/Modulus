"""Unit conversion IO layer.

All internal computation in MechOpt is SI (m, Pa, kg, N).
This module handles:
  - Input conversion: user-supplied values → SI
  - Output conversion: SI values → user display units
  - Display labels and formatted strings

Supported systems
-----------------
SI       : m, N, Pa, kg
MM       : mm, N, MPa, kg  (most common in mechanical engineering drawings)
IMPERIAL : in, lbf, psi, lb

Quantities
----------
"length"     : beam span, dimension, deflection result
"force"      : applied load P
"stress"     : sigma, sigma_y (Pa / MPa / psi)
"mass"       : weight output (kg / lb)
"deflection" : treated identically to length for conversion; kept as a
               separate quantity key so labels can differ from "length" if
               needed in the future.
"""

from enum import Enum


# ---------------------------------------------------------------------------
# Enum
# ---------------------------------------------------------------------------

class UnitSystem(Enum):
    SI       = "si"        # m, N, Pa, kg
    IMPERIAL = "imperial"  # in, lbf, psi, lb
    MM       = "mm"        # mm, N, MPa, kg


# ---------------------------------------------------------------------------
# Conversion constants (module-level, named for readability)
# ---------------------------------------------------------------------------

# --- to SI ---
MM_TO_M   = 1e-3
IN_TO_M   = 0.0254
LBF_TO_N  = 4.44822
PSI_TO_PA = 6894.76
KG_TO_LB  = 2.20462       # divide by this to convert lb → kg

# --- from SI ---
M_TO_MM   = 1000.0
M_TO_IN   = 39.3701
N_TO_LBF  = 0.224809
PA_TO_PSI = 1.45038e-4
PA_TO_MPA = 1e-6


# ---------------------------------------------------------------------------
# Input conversion: user units → SI
# ---------------------------------------------------------------------------

def convert_input(value: float, quantity: str, system: UnitSystem) -> float:
    """Convert a user-input value to SI.

    Parameters
    ----------
    value    : numeric value in the user's unit system
    quantity : one of "length", "force", "stress", "mass", "deflection"
    system   : the user's UnitSystem

    Returns
    -------
    float — value expressed in SI (m / N / Pa / kg)

    Raises
    ------
    ValueError if quantity or system is unrecognised.
    """
    quantity = quantity.lower()

    if system is UnitSystem.SI:
        # No conversion needed; validate quantity name for safety.
        _check_quantity(quantity)
        return float(value)

    if system is UnitSystem.MM:
        if quantity in ("length", "deflection"):
            return float(value) * MM_TO_M
        elif quantity == "stress":
            return float(value) * 1e6          # MPa → Pa
        elif quantity in ("force", "mass"):
            return float(value)                 # N and kg are unchanged in MM system
        else:
            _check_quantity(quantity)           # raises for unknown quantity

    if system is UnitSystem.IMPERIAL:
        if quantity in ("length", "deflection"):
            return float(value) * IN_TO_M
        elif quantity == "force":
            return float(value) * LBF_TO_N
        elif quantity == "stress":
            return float(value) * PSI_TO_PA
        elif quantity == "mass":
            return float(value) / KG_TO_LB     # lb → kg
        else:
            _check_quantity(quantity)

    raise ValueError(f"Unknown unit system: {system!r}")


# ---------------------------------------------------------------------------
# Output conversion: SI → user display units
# ---------------------------------------------------------------------------

def convert_output(value: float, quantity: str, system: UnitSystem) -> float:
    """Convert an SI value to the user's display units.

    Exact inverse of convert_input.

    Parameters
    ----------
    value    : numeric value in SI
    quantity : one of "length", "force", "stress", "mass", "deflection"
    system   : the target display UnitSystem

    Returns
    -------
    float — value expressed in the user's units
    """
    quantity = quantity.lower()

    if system is UnitSystem.SI:
        _check_quantity(quantity)
        return float(value)

    if system is UnitSystem.MM:
        if quantity in ("length", "deflection"):
            return float(value) * M_TO_MM
        elif quantity == "stress":
            return float(value) * PA_TO_MPA    # Pa → MPa
        elif quantity in ("force", "mass"):
            return float(value)
        else:
            _check_quantity(quantity)

    if system is UnitSystem.IMPERIAL:
        if quantity in ("length", "deflection"):
            return float(value) * M_TO_IN
        elif quantity == "force":
            return float(value) * N_TO_LBF
        elif quantity == "stress":
            return float(value) * PA_TO_PSI
        elif quantity == "mass":
            return float(value) * KG_TO_LB
        else:
            _check_quantity(quantity)

    raise ValueError(f"Unknown unit system: {system!r}")


# ---------------------------------------------------------------------------
# Display labels
# ---------------------------------------------------------------------------

_LABELS = {
    UnitSystem.SI: {
        "length":     "m",
        "force":      "N",
        "stress":     "Pa",
        "mass":       "kg",
        "deflection": "m",
    },
    UnitSystem.MM: {
        "length":     "mm",
        "force":      "N",
        "stress":     "MPa",
        "mass":       "kg",
        "deflection": "mm",
    },
    UnitSystem.IMPERIAL: {
        "length":     "in",
        "force":      "lbf",
        "stress":     "psi",
        "mass":       "lb",
        "deflection": "in",
    },
}

_VALID_QUANTITIES = frozenset(_LABELS[UnitSystem.SI].keys())


def unit_label(quantity: str, system: UnitSystem) -> str:
    """Return the display label for a quantity in the given unit system.

    Parameters
    ----------
    quantity : "length", "force", "stress", "mass", or "deflection"
    system   : UnitSystem

    Returns
    -------
    str — e.g. "mm", "MPa", "lbf"
    """
    quantity = quantity.lower()
    _check_quantity(quantity)
    return _LABELS[system][quantity]


# ---------------------------------------------------------------------------
# Formatted value string
# ---------------------------------------------------------------------------

def format_value(value: float, quantity: str, system: UnitSystem) -> str:
    """Format an SI value with its display unit label after converting.

    The value is first passed through convert_output, then formatted with
    one decimal place.

    Parameters
    ----------
    value    : numeric value in SI
    quantity : one of "length", "force", "stress", "mass", "deflection"
    system   : target display UnitSystem

    Returns
    -------
    str — e.g. "15.0 mm", "2175.8 psi", "0.003 m"

    Examples
    --------
    >>> format_value(0.015, "length", UnitSystem.MM)
    '15.0 mm'
    >>> format_value(250e6, "stress", UnitSystem.IMPERIAL)
    '36259.5 psi'
    """
    display_value = convert_output(value, quantity, system)
    label = unit_label(quantity, system)
    return f"{display_value:.1f} {label}"


# ---------------------------------------------------------------------------
# Internal helper
# ---------------------------------------------------------------------------

def _check_quantity(quantity: str) -> None:
    """Raise ValueError for an unrecognised quantity string."""
    if quantity not in _VALID_QUANTITIES:
        raise ValueError(
            f"Unknown quantity: {quantity!r}. "
            f"Valid quantities: {sorted(_VALID_QUANTITIES)}"
        )
