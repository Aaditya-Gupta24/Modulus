"""Bidirectional Streamlit custom component for interactive cross-section editing.

Wraps a static index.html that draws cross-sections as SVG and lets the user
edit dimensions via number inputs or drag handles. Data flows both ways:
  Python -> HTML: current section type, dimensions, computed results
  HTML -> Python: user-edited dimensions (triggers recomputation)
"""

import os

import streamlit.components.v1 as components

_COMPONENT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "section_editor")

_component_func = components.declare_component("section_editor", path=_COMPONENT_DIR)


def section_editor(section: str, dims: dict, results: dict, key=None):
    """Render the interactive cross-section editor.

    Parameters
    ----------
    section : str
        Section type name (rectangle, circle, hollow_circle, square_tube, i_beam).
    dims : dict
        Dimension parameters for the section (e.g. {"b": 0.03, "h": 0.03}).
    results : dict
        Computed results dict with keys: stress, deflection, fos, safe.
    key : str or None
        Streamlit widget key.

    Returns
    -------
    dict or None
        Updated dimensions from user interaction, or None on first render.
    """
    value = _component_func(
        section=section,
        dims=dims,
        results=results,
        key=key,
        default=None,
    )
    return value
