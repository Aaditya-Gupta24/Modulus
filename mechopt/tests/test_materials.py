"""Material database tests."""

import pytest
from modulus.materials import MATERIALS, Material

EXPECTED_KEYS = [
    "aluminum_6061", "steel_a36", "pla",
    "titanium_ti6al4v", "brass_360", "abs_plastic",
]


def test_all_expected_keys_exist():
    for key in EXPECTED_KEYS:
        assert key in MATERIALS, f"Missing material key: {key}"


@pytest.mark.parametrize("key", EXPECTED_KEYS)
def test_material_properties_positive(key):
    mat = MATERIALS[key]
    assert isinstance(mat, Material)
    assert mat.E > 0
    assert mat.sigma_y > 0
    assert mat.rho > 0
    assert mat.cost > 0
