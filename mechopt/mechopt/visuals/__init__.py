"""UI-only visual components for MechOpt (Streamlit front end).

Nothing in this package performs engineering calculations — it only renders
numbers that are already computed by the engine modules (beam.py, bracket.py,
optimizer.py, etc.) into SVG/HTML strings for display. Keep it that way:
visuals/ is presentation, not physics.
"""
