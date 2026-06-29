"""Oracle-first unit-conversion tests for mechopt.units.

All numeric targets are derived from hand-checked equations using the module's
documented constants:
  MM_TO_M   = 1e-3
  IN_TO_M   = 0.0254
  LBF_TO_N  = 4.44822
  PSI_TO_PA = 6894.76
  KG_TO_LB  = 2.20462
  M_TO_MM   = 1000.0
  M_TO_IN   = 39.3701
  N_TO_LBF  = 0.224809
  PA_TO_PSI = 1.45038e-4
  PA_TO_MPA = 1e-6

No target here was produced by running the implementation first.
"""

import pytest
from mechopt.units import (
    UnitSystem,
    convert_input,
    convert_output,
    unit_label,
    format_value,
    MM_TO_M,
    IN_TO_M,
    LBF_TO_N,
    PSI_TO_PA,
    KG_TO_LB,
)


# ---------------------------------------------------------------------------
# 1. UnitSystem enum membership
# ---------------------------------------------------------------------------

class TestUnitSystemEnum:
    def test_si_member_exists(self):
        assert UnitSystem.SI is not None

    def test_imperial_member_exists(self):
        assert UnitSystem.IMPERIAL is not None

    def test_mm_member_exists(self):
        assert UnitSystem.MM is not None

    def test_three_members_total(self):
        assert len(list(UnitSystem)) == 3


# ---------------------------------------------------------------------------
# 2. Module-level constants have correct values
# ---------------------------------------------------------------------------

class TestConstants:
    def test_mm_to_m(self):
        assert MM_TO_M == pytest.approx(1e-3)

    def test_in_to_m(self):
        assert IN_TO_M == pytest.approx(0.0254)

    def test_lbf_to_n(self):
        assert LBF_TO_N == pytest.approx(4.44822)

    def test_psi_to_pa(self):
        assert PSI_TO_PA == pytest.approx(6894.76)

    def test_kg_to_lb(self):
        assert KG_TO_LB == pytest.approx(2.20462)


# ---------------------------------------------------------------------------
# 3. convert_input — MM system
# ---------------------------------------------------------------------------

class TestConvertInputMM:
    def test_length_25_4_mm_to_m(self):
        # 25.4 mm * 1e-3 = 0.0254 m
        result = convert_input(25.4, "length", UnitSystem.MM)
        assert result == pytest.approx(0.0254, rel=1e-6)

    def test_stress_100_mpa_to_pa(self):
        # 100 MPa * 1e6 = 100e6 Pa
        result = convert_input(100.0, "stress", UnitSystem.MM)
        assert result == pytest.approx(100e6, rel=1e-6)

    def test_force_50_n_unchanged(self):
        # Force in MM system: N is unchanged
        result = convert_input(50.0, "force", UnitSystem.MM)
        assert result == pytest.approx(50.0, rel=1e-9)

    def test_mass_5_kg_unchanged(self):
        # Mass in MM system: kg is unchanged
        result = convert_input(5.0, "mass", UnitSystem.MM)
        assert result == pytest.approx(5.0, rel=1e-9)

    def test_deflection_treated_as_length_mm(self):
        # "deflection" is identical to "length" in conversion
        # 10 mm * 1e-3 = 0.01 m
        result = convert_input(10.0, "deflection", UnitSystem.MM)
        assert result == pytest.approx(0.01, rel=1e-6)


# ---------------------------------------------------------------------------
# 4. convert_input — IMPERIAL system
# ---------------------------------------------------------------------------

class TestConvertInputImperial:
    def test_length_1_inch_to_m(self):
        # 1 in * 0.0254 = 0.0254 m
        result = convert_input(1.0, "length", UnitSystem.IMPERIAL)
        assert result == pytest.approx(0.0254, rel=1e-6)

    def test_stress_100_psi_to_pa(self):
        # 100 psi * 6894.76 = 689476 Pa
        result = convert_input(100.0, "stress", UnitSystem.IMPERIAL)
        assert result == pytest.approx(689476.0, rel=1e-5)

    def test_force_10_lbf_to_n(self):
        # 10 lbf * 4.44822 = 44.4822 N
        result = convert_input(10.0, "force", UnitSystem.IMPERIAL)
        assert result == pytest.approx(44.4822, rel=1e-5)

    def test_mass_10_lb_to_kg(self):
        # 10 lb / 2.20462 = 4.53592... kg
        result = convert_input(10.0, "mass", UnitSystem.IMPERIAL)
        assert result == pytest.approx(10.0 / 2.20462, rel=1e-5)

    def test_deflection_treated_as_length_imperial(self):
        # "deflection" same as "length": 2 in * 0.0254 = 0.0508 m
        result = convert_input(2.0, "deflection", UnitSystem.IMPERIAL)
        assert result == pytest.approx(0.0508, rel=1e-6)


# ---------------------------------------------------------------------------
# 5. convert_input — SI system is identity
# ---------------------------------------------------------------------------

class TestConvertInputSI:
    def test_length_identity(self):
        assert convert_input(3.5, "length", UnitSystem.SI) == pytest.approx(3.5)

    def test_force_identity(self):
        assert convert_input(200.0, "force", UnitSystem.SI) == pytest.approx(200.0)

    def test_stress_identity(self):
        assert convert_input(250e6, "stress", UnitSystem.SI) == pytest.approx(250e6)

    def test_mass_identity(self):
        assert convert_input(7.85, "mass", UnitSystem.SI) == pytest.approx(7.85)

    def test_deflection_identity(self):
        assert convert_input(0.005, "deflection", UnitSystem.SI) == pytest.approx(0.005)


# ---------------------------------------------------------------------------
# 6. convert_output is exact inverse of convert_input
# ---------------------------------------------------------------------------

class TestConvertOutputIsInverse:
    """Round-trip: convert_output(convert_input(v, q, s), q, s) == v."""

    @pytest.mark.parametrize("quantity,value", [
        ("length",     25.4),
        ("stress",     100.0),
        ("force",      50.0),
        ("mass",       5.0),
        ("deflection", 10.0),
    ])
    def test_roundtrip_mm(self, quantity, value):
        si = convert_input(value, quantity, UnitSystem.MM)
        back = convert_output(si, quantity, UnitSystem.MM)
        assert back == pytest.approx(value, rel=1e-9)

    @pytest.mark.parametrize("quantity,value,rel_tol", [
        # IMPERIAL forward/backward constants are independently truncated values,
        # so round-trips are only exact to the precision of those constants.
        # IN_TO_M * M_TO_IN  = 0.0254 * 39.3701 = 0.99999954  -> ~5e-7 error -> rel=1e-4
        # LBF_TO_N * N_TO_LBF = 4.44822 * 0.224809 = ~0.99999889 -> rel=1e-4
        # PSI_TO_PA * PA_TO_PSI = 6894.76 * 1.45038e-4 = ~1.000022 -> rel=1e-3
        # KG_TO_LB is used as divide/multiply on the same path so mass round-trips exactly.
        ("length",     1.0,   1e-4),
        ("stress",     100.0, 1e-3),
        ("force",      10.0,  1e-4),
        ("mass",       10.0,  1e-9),   # lb->kg->lb uses same constant both ways
        ("deflection", 2.0,   1e-4),
    ])
    def test_roundtrip_imperial(self, quantity, value, rel_tol):
        si = convert_input(value, quantity, UnitSystem.IMPERIAL)
        back = convert_output(si, quantity, UnitSystem.IMPERIAL)
        assert back == pytest.approx(value, rel=rel_tol)

    @pytest.mark.parametrize("quantity,value", [
        ("length",     1.5),
        ("force",      300.0),
        ("stress",     250e6),
        ("mass",       2.7),
        ("deflection", 0.003),
    ])
    def test_roundtrip_si(self, quantity, value):
        si = convert_input(value, quantity, UnitSystem.SI)
        back = convert_output(si, quantity, UnitSystem.SI)
        assert back == pytest.approx(value, rel=1e-12)


# ---------------------------------------------------------------------------
# 7. unit_label returns correct strings
# ---------------------------------------------------------------------------

class TestUnitLabel:
    def test_si_length_label(self):
        assert unit_label("length", UnitSystem.SI) == "m"

    def test_si_force_label(self):
        assert unit_label("force", UnitSystem.SI) == "N"

    def test_si_stress_label(self):
        assert unit_label("stress", UnitSystem.SI) == "Pa"

    def test_si_mass_label(self):
        assert unit_label("mass", UnitSystem.SI) == "kg"

    def test_si_deflection_label(self):
        assert unit_label("deflection", UnitSystem.SI) == "m"

    def test_mm_length_label(self):
        assert unit_label("length", UnitSystem.MM) == "mm"

    def test_mm_force_label(self):
        assert unit_label("force", UnitSystem.MM) == "N"

    def test_mm_stress_label(self):
        assert unit_label("stress", UnitSystem.MM) == "MPa"

    def test_mm_mass_label(self):
        assert unit_label("mass", UnitSystem.MM) == "kg"

    def test_mm_deflection_label(self):
        assert unit_label("deflection", UnitSystem.MM) == "mm"

    def test_imperial_length_label(self):
        assert unit_label("length", UnitSystem.IMPERIAL) == "in"

    def test_imperial_force_label(self):
        assert unit_label("force", UnitSystem.IMPERIAL) == "lbf"

    def test_imperial_stress_label(self):
        assert unit_label("stress", UnitSystem.IMPERIAL) == "psi"

    def test_imperial_mass_label(self):
        assert unit_label("mass", UnitSystem.IMPERIAL) == "lb"

    def test_imperial_deflection_label(self):
        assert unit_label("deflection", UnitSystem.IMPERIAL) == "in"


# ---------------------------------------------------------------------------
# 8. format_value produces correct formatted strings
# ---------------------------------------------------------------------------

class TestFormatValue:
    def test_mm_length_format(self):
        # 0.015 m -> 15.0 mm
        assert format_value(0.015, "length", UnitSystem.MM) == "15.0 mm"

    def test_imperial_stress_format(self):
        # 250e6 Pa -> 250e6 * 1.45038e-4 = 36259.5 psi
        assert format_value(250e6, "stress", UnitSystem.IMPERIAL) == "36259.5 psi"

    def test_si_force_format(self):
        # 300.0 N in SI -> "300.0 N"
        assert format_value(300.0, "force", UnitSystem.SI) == "300.0 N"

    def test_mm_stress_format(self):
        # 200e6 Pa -> 200.0 MPa
        assert format_value(200e6, "stress", UnitSystem.MM) == "200.0 MPa"

    def test_imperial_force_format(self):
        # 44.4822 N -> 44.4822 * 0.224809 = 9.999... ≈ 10.0 lbf
        # Oracle: 44.4822 * 0.224809 = 9.9999...
        assert format_value(44.4822, "force", UnitSystem.IMPERIAL) == "10.0 lbf"


# ---------------------------------------------------------------------------
# 9. Error handling — invalid quantity and invalid system
# ---------------------------------------------------------------------------

class TestErrorHandling:
    def test_invalid_quantity_raises_valueerror_si(self):
        with pytest.raises(ValueError, match="Unknown quantity"):
            convert_input(1.0, "velocity", UnitSystem.SI)

    def test_invalid_quantity_raises_valueerror_mm(self):
        with pytest.raises(ValueError, match="Unknown quantity"):
            convert_input(1.0, "torque", UnitSystem.MM)

    def test_invalid_quantity_raises_valueerror_imperial(self):
        with pytest.raises(ValueError, match="Unknown quantity"):
            convert_input(1.0, "pressure", UnitSystem.IMPERIAL)

    def test_invalid_quantity_unit_label_raises_valueerror(self):
        with pytest.raises(ValueError, match="Unknown quantity"):
            unit_label("velocity", UnitSystem.SI)

    def test_invalid_quantity_convert_output_raises_valueerror(self):
        with pytest.raises(ValueError, match="Unknown quantity"):
            convert_output(1.0, "velocity", UnitSystem.SI)
