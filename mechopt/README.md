# MechOpt — Python-Based Mechanical Design Optimization Tool

[![CI](https://github.com/Aaditya-Gupta24/MechOpt/actions/workflows/ci.yml/badge.svg)](https://github.com/Aaditya-Gupta24/MechOpt/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.12-blue)
![Tests](https://img.shields.io/badge/tests-117%20passing-brightgreen)
![License](https://img.shields.io/badge/license-MIT-green)

**MechOpt screens beam and bracket designs across material, cross-section, and
dimensions, then recommends the best option under a chosen priority — lightest,
cheapest, highest factor of safety, or best-balanced — and visualizes the
weight–cost–strength tradeoffs.** It is a first-pass engineering decision tool,
backed by 117 automated tests and validated against an independent finite-element
solver.

🔗 **Live demo:** _(deploy to Streamlit Community Cloud and paste the URL here)_
&nbsp;·&nbsp; 📄 **[Validation report](validation/VALIDATION.md)**
&nbsp;·&nbsp; 📐 **[Case study](docs/CASE_STUDY.md)**
&nbsp;·&nbsp; 🧮 **[Engineering spec](SPEC.md)**

> _Add 2–3 screenshots and a short GIF of the optimizer + live section editor here —
> reviewers won't clone the repo, so the visuals carry the first impression._

## What it does

Given a load, span, load case, and a target factor of safety, MechOpt:

1. Computes stress, deflection, and factor of safety for every candidate design.
2. Filters to the designs that are actually safe (FoS ≥ target).
3. Picks winners: lightest safe, cheapest safe, highest FoS, and best-balanced.
4. Plots weight vs. cost vs. strength tradeoffs (Pareto view).
5. Prints a short, reasoned design recommendation.

The Streamlit app has four tabs: **Beam Optimizer**, **Bracket Analysis**,
**Compare Designs**, and **Assumptions & Limitations**. The Beam Optimizer
includes a **bidirectional custom component** — an SVG section editor where
editing a dimension sends new geometry back to Python, which recomputes stress
and FoS live.

## Validation — why you can trust the numbers

Passing tests only prove the code matches my own equations. To prove the
*equations* are right, MechOpt is checked two independent ways
([full report](validation/VALIDATION.md)):

- **Against an independent FE solver.** `validation/fea_beam.py` is a from-scratch
  1-D finite-element beam solver (direct-stiffness, Hermite cubic elements) that
  shares no code with the analytical model. The analytical deflections and moments
  match it to **within 1×10⁻⁴ %** across solid, tube, and I-sections.
- **Against a higher-fidelity theory.** Comparing Euler–Bernoulli to Timoshenko
  (shear-corrected) beam theory quantifies the assumption error: **< 0.4 % for
  slender beams (L/h ≳ 15)**, rising for stubby members — a known, bounded limit
  that the app surfaces in its Assumptions tab.

![Validation](validation/validation.png)

## Engineering basis

| Quantity              | Equation                                         |
|-----------------------|--------------------------------------------------|
| Rectangle I           | b·h³ / 12                                         |
| Circle I              | π·d⁴ / 64                                         |
| I-beam I              | (b·h³ − (b−tw)(h−2tf)³) / 12                      |
| Square tube I         | (a⁴ − ai⁴) / 12,  ai = a−2w                       |
| Hollow rectangle I    | (b·h³ − bi·hi³) / 12,  bi = b−2w, hi = h−2w       |
| Hollow circle I       | π·(d⁴ − di⁴) / 64                                 |
| Bending stress        | σ = M·c / I                                       |
| Cantilever, end load  | M = P·L,  δ = P·L³ / (3·E·I)                      |
| Simply sup., center   | M = P·L/4,  δ = P·L³ / (48·E·I)                   |
| Factor of safety      | FoS = σ_yield / σ                                 |
| Weight / cost         | A·L·ρ ,  weight × cost-per-kg                     |

## Worked example

**Case A** — Steel A36, solid 30×30 mm square, span L = 0.8 m, P = 300 N end load
(cantilever): I = 6.75×10⁻⁸ m⁴, σ ≈ 53.3 MPa, δ ≈ 3.79 mm, FoS ≈ 4.69 (safe).

These exact figures are pinned as known-answer tests in `tests/`, and the
deflection is independently reproduced by the FE solver above.

## Assumptions

Linear-elastic material, small-deflection (Euler–Bernoulli) theory, static point
load, prismatic beam. Material property values are **nominal** grade values, not
vendor datasheet figures; cost figures are rough and market-dependent.

## Limitations (not modeled)

Local/wall buckling, stress concentrations, fatigue, dynamic/impact loading, and
joint/weld effects. (Shear deflection is not in the model but is *quantified* in
the [validation report](validation/VALIDATION.md), and global **Euler column
buckling** for compression members is available via `mechopt/buckling.py`.)
MechOpt is a first-pass screening tool, not a substitute for detailed analysis or
review by a qualified engineer.

## Run it

```bash
pip install -r requirements.txt
pytest -v                                          # run the full test suite
streamlit run app.py                               # launch the web app
PYTHONPATH=. python validation/run_validation.py   # reproduce the validation report
```

## Project layout

```
mechopt/
  mechopt/        core library
    materials.py    material property database
    sections.py     6 cross-sections → SectionProps(A, I, c)
    beam.py         moment, stress, deflection, factor of safety
    buckling.py     Euler column buckling for compression members
    bracket.py      simplified bracket: plate bending + bolt group
    optimizer.py    design-space sweep + recommendation logic
    components/     bidirectional Streamlit SVG section editor
  validation/     independent FE solver + validation report + plot
  tests/          117 pytest known-answer + behavioral + cross-validation tests
  app.py          Streamlit UI (4 tabs)
  SPEC.md         build contract / engineering spec
  .github/        CI (runs pytest on every push)   ← workflow lives at repo root
```

## License

MIT © 2026 Aaditya Gupta
