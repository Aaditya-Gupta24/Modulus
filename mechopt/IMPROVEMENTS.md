# MechOpt Improvement Plan

## Highest Impact

1. Add validation tests for invalid loads, spans, dimensions, material filters, and priorities. Several core functions validate some geometry, but the project should consistently reject non-physical inputs at module boundaries.
2. Add analytical depth: Euler buckling, deflection-limit defaults such as `L/360`, and asymmetric T/L sections using neutral-axis and parallel-axis calculations.
3. Add independent validation: compare one beam and one bracket case against a spreadsheet, textbook worked example, or simple FEA result and document the percent error.
4. Add parity checks for the standalone `index.html` dashboard. Python is the oracle, so the JavaScript physics should be checked against Python outputs for representative rectangle, tube, and I-beam cases.
5. Turn this into a standard Python project with `pyproject.toml`, pinned or locked dependencies, and commands for tests and app launch.

## Portfolio Polish

1. Move from "calculator" to "engineering story": include a case study where the optimizer explains why a tube beats a solid section for bending efficiency.
2. Add screenshots or a short GIF to the README.
3. Add a technical report notebook or PDF that shows assumptions, equations, plots, and limitations in one clean narrative.
4. Deploy the Streamlit app and link it from the README.
5. Keep limitations prominent: no fatigue, buckling interaction, stress concentrations, welds, bearing, tear-out, or certified design review.

## Code Quality

1. Reduce duplicated candidate-row construction in `optimizer.py` by adding a small internal helper.
2. Remove or implement dead placeholders such as unused `NotImplementedError` helpers once tests no longer need them.
3. Keep UI helper functions pure and tested; avoid placing engineering calculations directly in `app.py`.
4. Add type hints for public APIs and run a lightweight type checker later.
5. Keep generated caches and logs out of git via `.gitignore`.

## Suggested Next Test Loops

1. "Invalid non-positive beam loads raise `ValueError` across `beam.py` and `optimizer.py`."
2. "Buckling safety is reported for slender compression members with one known-answer Euler case."
3. "The HTML dashboard matches Python for three fixed default cases to displayed precision."
4. "A T-section returns correct centroid, area, `I`, and extreme-fiber distances from a hand-derived target."
