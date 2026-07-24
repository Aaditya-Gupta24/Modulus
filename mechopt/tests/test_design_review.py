"""Oracle-first tests for the design_review module (Milestone D).

These tests encode hand-derived oracle targets for the Beam A reference
case (steel_a36, rectangle 30x30 mm, L=0.8 m, P=300 N, cantilever,
fos_target=1.5, deflection_limit=0.010 m).  The module under test does
NOT exist yet -- importing it will fail until design_review.py is
implemented.  That is intentional (red-green-refactor).

Oracle derivations are documented inline next to each assertion.
"""

import pytest
from modulus.optimizer import evaluate_candidates, recommend
from modulus.design_review import generate_review, DesignReview, SensitivityResult


# ---------------------------------------------------------------------------
# Helper -- Beam A review generator
# ---------------------------------------------------------------------------

def _generate_beam_a_review(**kwargs):
    """Generate a review for the Beam A oracle case.

    Beam A: steel_a36, rectangle, 30x30 mm, L=0.8 m, P=300 N,
    cantilever_end, fos_target=1.5, deflection_limit=0.010 m.
    """
    defaults = dict(
        load=300.0, length=0.8, load_case="cantilever_end", fos_target=1.5,
        material_keys=["steel_a36"], section_types=["rectangle"],
        deflection_limit=0.010,
    )
    defaults.update(kwargs)
    defl = defaults.pop("deflection_limit")
    mat_keys = defaults.pop("material_keys")
    sec_types = defaults.pop("section_types")

    df = evaluate_candidates(
        defaults["load"], defaults["length"], defaults["load_case"],
        defaults["fos_target"],
        material_keys=mat_keys, section_types=sec_types,
        deflection_limit=defl,
    )
    rec = recommend(df, "balanced")
    return generate_review(
        winner=rec, df=df, priority="balanced",
        load=defaults["load"], length=defaults["length"],
        load_case=defaults["load_case"], fos_target=defaults["fos_target"],
        deflection_limit=defl,
    )


# ---------------------------------------------------------------------------
# 1. Controlling constraint is deflection for Beam A
# ---------------------------------------------------------------------------

def test_review_beam_a_controlling_constraint():
    """Deflection is the controlling constraint for Beam A.

    Oracle derivation (PROJECT_CONTEXT section 7):
      For steel_a36 rectangle 30x30 mm cantilever at L=0.8 m, P=300 N:
        bending FoS ~ 3.875  (well above 1.5)
        deflection  ~ 6.207 mm vs limit 10.0 mm  -> margin ~ 0.6207
      Deflection margin (0.6207) < bending margin ((3.875 - 1.5) / 1.5 ~ 1.583)
      so deflection controls.
    """
    review = _generate_beam_a_review()

    assert isinstance(review, DesignReview)
    assert review.controlling_constraint == "deflection"
    assert review.controlling_margin == pytest.approx(0.6207, rel=1e-2)


# ---------------------------------------------------------------------------
# 2. Unmodeled risks include torsion (shear is now modeled)
# ---------------------------------------------------------------------------

def test_review_lists_unmodeled_risks():
    """The review must flag torsion as unmodeled (no torque input).

    Shear is now actively modeled. Torsion remains NOT_MODELED when no
    torque is applied, so the review must still warn about it.
    """
    review = _generate_beam_a_review()

    assert "shear" not in review.unmodeled_risks
    assert "torsion" in review.unmodeled_risks


# ---------------------------------------------------------------------------
# 3. Sensitivities are computed
# ---------------------------------------------------------------------------

def test_review_has_sensitivities():
    """The review must include at least one sensitivity result and
    identify the most important parameter.

    Each SensitivityResult must carry parameter name, fos_change, and
    deflection_change from a +5% bump of a geometric dimension.
    """
    review = _generate_beam_a_review()

    assert len(review.sensitivities) > 0
    assert isinstance(review.most_important_sensitivity, str)
    assert len(review.most_important_sensitivity) > 0

    for s in review.sensitivities:
        assert isinstance(s, SensitivityResult)
        assert isinstance(s.parameter, str)
        assert len(s.parameter) > 0
        assert isinstance(s.fos_change, float)
        assert isinstance(s.deflection_change, float)


# ---------------------------------------------------------------------------
# 4. Nearest alternative is present and different from winner
# ---------------------------------------------------------------------------

def test_review_has_nearest_alternative():
    """When multiple safe candidates exist, the review should identify
    the nearest alternative (2nd-ranked candidate).

    Use all section types to guarantee multiple safe options.
    """
    review = _generate_beam_a_review(
        section_types=["rectangle", "circle", "square_tube", "i_beam"],
    )

    assert review.nearest_alternative is not None
    assert review.nearest_alternative != review.recommended


# ---------------------------------------------------------------------------
# 5. Recommended next step mentions stiffness/deflection
# ---------------------------------------------------------------------------

def test_review_recommended_next_step():
    """Since deflection controls for Beam A, the recommended next step
    should advise on improving stiffness or deflection performance.
    """
    review = _generate_beam_a_review()

    assert isinstance(review.recommended_next_step, str)
    assert len(review.recommended_next_step) > 0
    step_lower = review.recommended_next_step.lower()
    assert "stiffness" in step_lower or "deflection" in step_lower


# ---------------------------------------------------------------------------
# 6. Explanation mentions the controlling constraint
# ---------------------------------------------------------------------------

def test_review_why_it_won():
    """The 'why_it_won' narrative must be a non-empty string that
    references the controlling constraint (deflection for Beam A).
    """
    review = _generate_beam_a_review()

    assert isinstance(review.why_it_won, str)
    assert len(review.why_it_won) > 0
    assert "deflection" in review.why_it_won.lower()


# ---------------------------------------------------------------------------
# 7. Recommended string contains material and section type
# ---------------------------------------------------------------------------

def test_review_recommended_format():
    """The 'recommended' field must mention the material name and the
    section type so users can identify the design at a glance.
    """
    review = _generate_beam_a_review()

    rec_lower = review.recommended.lower()
    # steel_a36 should appear (possibly as "steel a36" or "Steel A36")
    assert "steel" in rec_lower or "a36" in rec_lower
    assert "rectangle" in rec_lower or "rect" in rec_lower
