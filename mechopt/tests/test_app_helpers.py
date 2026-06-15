"""Tests for app.py UI helper functions.

These tests verify the pure helper functions in app.py: HTML/SVG generation,
utilisation-bar percentage logic, scatter-plot construction, and the
card/table builders.

Strategy: since app.py has Streamlit calls at module level, we extract just
the helper functions and constants via AST, then exec them in an isolated
namespace so no Streamlit import is needed.
"""

import ast
import textwrap

import pandas as pd
import plotly.graph_objects as go
import pytest


# ── Extract helpers from app.py without importing it ─────────────────────────

def _load_app_helpers():
    """Parse app.py, pull out constants + helper functions, return a namespace."""
    with open("app.py", encoding="utf-8") as f:
        source = f.read()
    tree = ast.parse(source)

    # Names we want to extract (constants + functions)
    WANTED_NAMES = {
        "ACCENT", "ACCENT_HEX", "MAT_CLR", "PLOTLY_COLORS",
        "PLOTLY_LAYOUT",
        "mdot", "section_svg", "bracket_svg", "util_bar",
        "scatter_plot", "card", "CARD_END",
    }

    # Collect top-level assignments and function defs we care about
    kept_nodes = []
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name in WANTED_NAMES:
            kept_nodes.append(node)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in WANTED_NAMES:
                    kept_nodes.append(node)

    # Build a mini-module with just those nodes
    mini = ast.Module(body=kept_nodes, type_ignores=[])
    ast.fix_missing_locations(mini)
    code = compile(mini, "app.py", "exec")

    ns = {"__builtins__": __builtins__}
    # Provide imports the helpers need
    import math
    import plotly.graph_objects as go_mod
    ns["math"] = math
    ns["go"] = go_mod
    exec(code, ns)
    return ns


@pytest.fixture(scope="module")
def h():
    """Namespace containing all app.py helper functions and constants."""
    return _load_app_helpers()


# ═════════════════════════════════════════════════════════════════════════════
# mdot()
# ═════════════════════════════════════════════════════════════════════════════

class TestMdot:
    def test_known_material_returns_correct_color(self, h):
        html = h["mdot"]("Steel A36")
        assert "#6b7280" in html
        assert 'class="mdot"' in html

    def test_unknown_material_uses_fallback_color(self, h):
        html = h["mdot"]("Unobtainium")
        assert "#6b7280" in html

    def test_all_materials_have_dot(self, h):
        for name, color in h["MAT_CLR"].items():
            html = h["mdot"](name)
            assert color in html


# ═════════════════════════════════════════════════════════════════════════════
# section_svg()
# ═════════════════════════════════════════════════════════════════════════════

class TestSectionSvg:
    SECTION_TYPES = [
        "rectangle", "circle", "i_beam",
        "square_tube", "hollow_rectangle", "hollow_circle",
    ]

    @pytest.mark.parametrize("sec", SECTION_TYPES)
    def test_returns_valid_svg(self, h, sec):
        svg = h["section_svg"](sec)
        assert svg.startswith("<svg")
        assert svg.endswith("</svg>")

    @pytest.mark.parametrize("sec", SECTION_TYPES)
    def test_default_size_is_104(self, h, sec):
        svg = h["section_svg"](sec, size=104)
        assert 'width="104"' in svg
        assert 'height="104"' in svg

    def test_custom_size(self, h):
        svg = h["section_svg"]("circle", size=64)
        assert 'width="64"' in svg

    def test_rectangle_contains_rect_element(self, h):
        assert "<rect" in h["section_svg"]("rectangle")

    def test_circle_contains_circle_element(self, h):
        assert "<circle" in h["section_svg"]("circle")

    def test_hollow_circle_has_two_circles(self, h):
        assert h["section_svg"]("hollow_circle").count("<circle") == 2

    def test_hollow_rectangle_has_two_rects(self, h):
        assert h["section_svg"]("hollow_rectangle").count("<rect") == 2

    def test_i_beam_has_three_rects(self, h):
        assert h["section_svg"]("i_beam").count("<rect") == 3

    def test_square_tube_has_two_rects(self, h):
        assert h["section_svg"]("square_tube").count("<rect") == 2

    def test_unknown_type_returns_empty_string(self, h):
        assert h["section_svg"]("nonexistent") == ""


# ═════════════════════════════════════════════════════════════════════════════
# bracket_svg()
# ═════════════════════════════════════════════════════════════════════════════

class TestBracketSvg:
    def test_returns_valid_svg(self, h):
        svg = h["bracket_svg"]()
        assert svg.startswith("<svg")
        assert "</svg>" in svg

    def test_contains_load_label(self, h):
        assert ">P<" in h["bracket_svg"]()

    def test_contains_offset_label(self, h):
        assert "offset e" in h["bracket_svg"]()

    def test_has_bolt_circles(self, h):
        assert h["bracket_svg"]().count("<circle") == 4


# ═════════════════════════════════════════════════════════════════════════════
# util_bar()
# ═════════════════════════════════════════════════════════════════════════════

class TestUtilBar:
    def test_zero_value_shows_zero_percent(self, h):
        html = h["util_bar"]("Test", 0, max_val=1.0)
        assert "0%" in html

    def test_full_value_shows_100_percent(self, h):
        assert "100%" in h["util_bar"]("Test", 1.0, max_val=1.0)

    def test_half_value_shows_50_percent(self, h):
        assert "50%" in h["util_bar"]("Test", 0.5, max_val=1.0)

    def test_value_above_max_is_clamped(self, h):
        assert "100%" in h["util_bar"]("Test", 2.0, max_val=1.0)

    def test_label_is_present(self, h):
        assert "Stress capacity" in h["util_bar"]("Stress capacity", 0.5)

    def test_invert_false_low_value_is_red(self, h):
        # Non-inverted: low = bad = red
        assert "#f87171" in h["util_bar"]("T", 0.2, invert=False)

    def test_invert_false_high_value_is_green(self, h):
        assert "#34d399" in h["util_bar"]("T", 0.9, invert=False)

    def test_invert_true_low_value_is_green(self, h):
        # Inverted: low utilisation = good = green
        assert "#34d399" in h["util_bar"]("T", 0.3, invert=True)

    def test_invert_true_high_value_is_red(self, h):
        assert "#f87171" in h["util_bar"]("T", 0.95, invert=True)

    def test_invert_true_mid_value_is_amber(self, h):
        assert "#fbbf24" in h["util_bar"]("T", 0.7, invert=True)

    def test_zero_max_val_returns_zero_percent(self, h):
        assert "0%" in h["util_bar"]("T", 5.0, max_val=0)

    def test_contains_css_classes(self, h):
        html = h["util_bar"]("T", 0.5)
        assert 'class="ub"' in html
        assert 'class="ub-track"' in html
        assert 'class="ub-fill"' in html


# ═════════════════════════════════════════════════════════════════════════════
# card() / CARD_END
# ═════════════════════════════════════════════════════════════════════════════

class TestCard:
    def test_card_with_title(self, h):
        html = h["card"]("My Section")
        assert "My Section" in html
        assert 'class="card-hd"' in html
        assert 'class="card"' in html

    def test_card_without_title(self, h):
        html = h["card"]()
        assert "card-hd" not in html
        assert 'class="card"' in html

    def test_card_end_closes_div(self, h):
        assert h["CARD_END"] == "</div>"

    def test_card_opens_div(self, h):
        assert h["card"]("X").startswith('<div class="card">')


# ═════════════════════════════════════════════════════════════════════════════
# scatter_plot()
# ═════════════════════════════════════════════════════════════════════════════

def _sample_df():
    """Small DataFrame mimicking evaluate_candidates output."""
    return pd.DataFrame([
        {"material": "Steel A36", "section": "rectangle", "dims": "30x30 mm",
         "area": 9e-4, "I": 6.75e-8, "weight": 0.5, "cost": 0.5,
         "stress": 5e7, "deflection": 0.001, "fos": 5.0, "safe": True},
        {"material": "Steel A36", "section": "circle", "dims": "d=20 mm",
         "area": 3.14e-4, "I": 7.85e-9, "weight": 0.2, "cost": 0.2,
         "stress": 2e8, "deflection": 0.01, "fos": 1.2, "safe": False},
        {"material": "Aluminum 6061-T6", "section": "rectangle",
         "dims": "40x40 mm", "area": 1.6e-3, "I": 2.13e-7,
         "weight": 0.3, "cost": 1.0, "stress": 3e7, "deflection": 0.002,
         "fos": 9.0, "safe": True},
    ])


class TestScatterPlot:
    def test_returns_plotly_figure(self, h):
        fig = h["scatter_plot"](_sample_df(), "weight", "fos", "W", "FoS",
                                2.0, "Title")
        assert isinstance(fig, go.Figure)

    def test_has_correct_title(self, h):
        fig = h["scatter_plot"](_sample_df(), "weight", "fos", "W", "FoS",
                                2.0, "My Title")
        assert fig.layout.title.text == "My Title"

    def test_unsafe_trace_present(self, h):
        fig = h["scatter_plot"](_sample_df(), "weight", "fos", "W", "FoS",
                                2.0, "T")
        assert "Unsafe" in [t.name for t in fig.data]

    def test_safe_materials_have_traces(self, h):
        fig = h["scatter_plot"](_sample_df(), "weight", "fos", "W", "FoS",
                                2.0, "T")
        names = [t.name for t in fig.data]
        assert "Steel A36" in names
        assert "Aluminum 6061-T6" in names

    def test_all_safe_df_no_unsafe_trace(self, h):
        df = _sample_df()
        df["safe"] = True
        fig = h["scatter_plot"](df, "weight", "fos", "W", "FoS", 2.0, "T")
        assert "Unsafe" not in [t.name for t in fig.data]

    def test_rec_row_adds_ring_marker(self, h):
        df = _sample_df()
        fig = h["scatter_plot"](df, "weight", "fos", "W", "FoS", 2.0, "T",
                                rec_row=df.iloc[0])
        ring = [t for t in fig.data if t.name == "Recommended"]
        assert len(ring) == 1

    def test_fos_target_line_on_fos_axis(self, h):
        fig = h["scatter_plot"](_sample_df(), "weight", "fos", "W", "FoS",
                                2.0, "T")
        shapes = fig.layout.shapes
        assert len(shapes) >= 1
        assert any(s.y0 == 2.0 for s in shapes)

    def test_no_fos_line_on_non_fos_axis(self, h):
        fig = h["scatter_plot"](_sample_df(), "weight", "cost", "W", "$",
                                2.0, "T")
        shapes = fig.layout.shapes or []
        assert len(shapes) == 0

    def test_single_safe_row(self, h):
        df = pd.DataFrame([{
            "material": "Steel A36", "section": "rectangle",
            "dims": "30x30 mm", "area": 9e-4, "I": 6.75e-8,
            "weight": 0.5, "cost": 0.5, "stress": 5e7,
            "deflection": 0.001, "fos": 5.0, "safe": True,
        }])
        fig = h["scatter_plot"](df, "weight", "fos", "W", "FoS", 2.0, "T")
        assert isinstance(fig, go.Figure)
        assert len(fig.data) >= 1


# ═════════════════════════════════════════════════════════════════════════════
# Constants & config
# ═════════════════════════════════════════════════════════════════════════════

class TestConstants:
    def test_mat_clr_covers_all_materials(self, h):
        from mechopt.materials import MATERIALS
        for m in MATERIALS.values():
            assert m.name in h["MAT_CLR"], f"Missing color for {m.name}"

    def test_accent_hex_is_valid(self, h):
        assert h["ACCENT_HEX"].startswith("#")
        assert len(h["ACCENT_HEX"]) == 7

    def test_plotly_layout_keys(self, h):
        for key in ("paper_bgcolor", "plot_bgcolor", "font", "margin",
                     "legend", "xaxis", "yaxis", "hoverlabel"):
            assert key in h["PLOTLY_LAYOUT"]
