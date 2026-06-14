"""Material property database.

Values are NOMINAL room-temperature properties for typical grades, suitable
for a student design-screening tool. They are not a substitute for a vendor
datasheet on a real part.

Units (SI):
    E        Young's modulus            [Pa]
    sigma_y  yield strength             [Pa]
    rho      density                    [kg/m^3]
    cost     approximate material cost  [USD/kg]
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Material:
    name: str
    E: float          # Pa
    sigma_y: float    # Pa
    rho: float        # kg/m^3
    cost: float       # USD/kg


# Nominal values. cost figures are rough order-of-magnitude and will drift with
# the market — treat as relative, not absolute. Document this in the README.
MATERIALS = {
    "aluminum_6061": Material("Aluminum 6061-T6", E=69e9,  sigma_y=275e6, rho=2700, cost=3.5),
    "steel_a36":     Material("Steel A36",        E=200e9, sigma_y=250e6, rho=7850, cost=1.0),
    "pla":           Material("PLA (3D print)",   E=3.5e9, sigma_y=50e6,  rho=1240, cost=25.0),
}
