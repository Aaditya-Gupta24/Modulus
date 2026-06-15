"""Tests for the section_editor component module.

These tests verify the Python-side wiring of the bidirectional Streamlit custom
component. The actual postMessage handshake runs only inside a browser and
cannot be unit-tested, so we do NOT fake coverage for it.
"""

import os

from mechopt.components.section_editor import section_editor, _COMPONENT_DIR


def test_component_module_imports():
    """The section_editor function is importable from the component package."""
    assert callable(section_editor)


def test_declare_component_path_exists():
    """The HTML directory passed to declare_component must exist and contain
    index.html."""
    assert os.path.isdir(_COMPONENT_DIR)
    assert os.path.isfile(os.path.join(_COMPONENT_DIR, "index.html"))


def test_index_html_contains_component_protocol():
    """index.html must implement the Streamlit component message protocol:
    componentReady, setFrameHeight, and setComponentValue."""
    html_path = os.path.join(_COMPONENT_DIR, "index.html")
    with open(html_path, encoding="utf-8") as f:
        html = f.read()
    assert "streamlit:componentReady" in html
    assert "streamlit:setFrameHeight" in html
    assert "streamlit:setComponentValue" in html
    assert "streamlit:render" in html


def test_index_html_contains_svg_builders():
    """index.html must have SVG drawing functions for all supported section
    types."""
    html_path = os.path.join(_COMPONENT_DIR, "index.html")
    with open(html_path, encoding="utf-8") as f:
        html = f.read()
    for section in ["rectangle", "circle", "hollow_circle", "square_tube", "i_beam"]:
        # Each section type should have a dedicated SVG builder function
        func_name = "svg" + section.replace("_", " ").title().replace(" ", "")
        assert func_name in html, f"Missing SVG builder for {section}: {func_name}"
