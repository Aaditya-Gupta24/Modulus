"""Golden + structural tests for the SVG diagram generators (mechopt.visuals).

``render_beam_svg`` and ``render_bracket_svg`` are deterministic string builders,
so these are snapshot tests: we pin each render's exact output in a checked-in
golden file to catch silent drift (e.g. a colour or geometry change), and we
separately parse every render as XML so malformed markup or invalid entities
fail loudly.

To intentionally update the golden after a deliberate visual change, run:

    UPDATE_VISUALS_GOLDEN=1 python -m pytest tests/test_visuals.py

then review the diff of tests/data/visuals_golden.json before committing.
"""

import json
import os
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

from mechopt.visuals.beam_svg import render_beam_svg
from mechopt.visuals.bracket_svg import render_bracket_svg

GOLDEN_PATH = Path(__file__).parent / "data" / "visuals_golden.json"
SVG_ROOT = "{http://www.w3.org/2000/svg}svg"

BEAM_LOAD_CASES = ["cantilever_end", "cantilever_udl", "simply_center", "simply_udl"]
# Engine section keys (sections.py function names); the renderer matches these
# exactly and falls back to a plain rectangle for anything else.
BEAM_SECTIONS = ["rectangle", "circle", "i_beam", "hollow_rectangle", "square_tube", "hollow_circle"]
BRACKET_CONSTRAINTS = [None, "plate_bending", "bolt_shear", "euler_buckling"]


def _beam_cases():
    # One render per section type (cantilever_end) guards each section shape.
    for sec in BEAM_SECTIONS:
        yield f"beam-{sec}-plain", (
            lambda sec=sec: render_beam_svg("cantilever_end", 1.5, 1500.0, sec, "Steel A36")
        )
    # One deflection+stress overlay per load case guards each load case and the
    # PASS-badge caption path (the deflection caption uses numeric char refs).
    for lc in BEAM_LOAD_CASES:
        yield f"beam-{lc}-overlay", (
            lambda lc=lc: render_beam_svg(
                lc, 1.5, 1500.0, "rectangle", "Aluminum 6061-T6",
                max_deflection_m=0.004, deflection_limit_m=0.01, stress_ratio=0.62,
            )
        )
    # Deflection past the limit exercises the FAIL-badge branch.
    yield "beam-cantilever_end-defl-fail", (
        lambda: render_beam_svg(
            "cantilever_end", 2.0, 3000.0, "rectangle", "PLA (3D print)",
            max_deflection_m=0.05, deflection_limit_m=0.01, stress_ratio=0.9,
        )
    )


def _bracket_cases():
    # Controlling-constraint badge matrix. `safe` affects output only via the
    # badge colour (RED when safe is False, else AMBER) and only when a
    # constraint is set — so safe=True/None render identically and ctrl=None is
    # safe-independent. The redundant combinations are kept to pin those
    # invariants (a future change that lets `safe` leak elsewhere would break).
    for ctrl in BRACKET_CONSTRAINTS:
        for safe in (True, False, None):
            yield f"bracket-ctrl_{ctrl}-safe_{safe}", (
                lambda ctrl=ctrl, safe=safe: render_bracket_svg(
                    load_n=2000.0, offset_m=0.15, plate_width_m=0.08,
                    plate_thickness_m=0.008, bolt_count=4, bolt_spacing_m=0.04,
                    controlling_constraint=ctrl, worst_bolt_index=0, safe=safe,
                )
            )
    # Bolt-count variations guard the bolt-group layout.
    for nb in (1, 2, 6):
        yield f"bracket-bolts_{nb}", (
            lambda nb=nb: render_bracket_svg(
                load_n=2000.0, offset_m=0.15, plate_width_m=0.08,
                plate_thickness_m=0.008, bolt_count=nb, bolt_spacing_m=0.04,
                controlling_constraint="bolt_shear", worst_bolt_index=0, safe=True,
            )
        )


ALL_CASES = list(_beam_cases()) + list(_bracket_cases())
CASE_IDS = [key for key, _ in ALL_CASES]


def _load_golden():
    if GOLDEN_PATH.exists():
        return json.loads(GOLDEN_PATH.read_text(encoding="utf-8"))
    return {}


def _first_diff(expected, actual):
    for i, (e, a) in enumerate(zip(expected, actual)):
        if e != a:
            lo = max(0, i - 40)
            return (f"first difference at index {i}\n"
                    f"  expected ...{expected[lo:i + 40]!r}\n"
                    f"  actual   ...{actual[lo:i + 40]!r}")
    if len(expected) != len(actual):
        return f"length differs: expected {len(expected)}, actual {len(actual)}"
    return "identical"


GOLDEN = _load_golden()


@pytest.mark.parametrize("key,render", ALL_CASES, ids=CASE_IDS)
def test_render_is_wellformed_svg(key, render):
    """Every render parses as XML with an <svg> root — guards malformed markup
    and invalid (non-XML) entities."""
    svg = render()
    assert svg.lstrip().startswith("<svg"), f"{key}: does not start with <svg"
    assert svg.rstrip().endswith("</svg>"), f"{key}: does not end with </svg>"
    root = ET.fromstring(svg)  # raises ParseError on malformed XML / bad entities
    assert root.tag == SVG_ROOT, f"{key}: unexpected root {root.tag}"


@pytest.mark.parametrize("key,render", ALL_CASES, ids=CASE_IDS)
def test_render_matches_golden(key, render):
    """Render output is byte-for-byte identical to the checked-in golden."""
    assert GOLDEN, (
        "golden file missing/empty; generate it with "
        "UPDATE_VISUALS_GOLDEN=1 python -m pytest tests/test_visuals.py"
    )
    assert key in GOLDEN, f"no golden entry for {key!r}; regenerate the golden file"
    actual = render()
    assert actual == GOLDEN[key], (
        f"SVG output for {key!r} changed.\n{_first_diff(GOLDEN[key], actual)}\n"
        "If this change is intentional, regenerate with "
        "UPDATE_VISUALS_GOLDEN=1 python -m pytest tests/test_visuals.py"
    )


def test_golden_has_no_orphan_entries():
    """The golden file contains exactly the current case keys — a removed or
    renamed case must not leave a stale golden entry behind."""
    assert set(GOLDEN) == set(CASE_IDS), (
        f"golden keys differ from cases; "
        f"missing={sorted(set(CASE_IDS) - set(GOLDEN))}, "
        f"orphaned={sorted(set(GOLDEN) - set(CASE_IDS))}"
    )


def test_regenerate_golden():
    """Rewrites the golden file. Skipped unless UPDATE_VISUALS_GOLDEN=1 so a
    normal run never masks drift by silently overwriting the baseline."""
    if os.environ.get("UPDATE_VISUALS_GOLDEN") != "1":
        pytest.skip("set UPDATE_VISUALS_GOLDEN=1 to rewrite the golden file")
    data = {key: render() for key, render in ALL_CASES}
    GOLDEN_PATH.parent.mkdir(parents=True, exist_ok=True)
    GOLDEN_PATH.write_text(
        json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
