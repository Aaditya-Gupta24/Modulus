# MechOpt — Python-Based Mechanical Design Optimization Tool

MechOpt screens beam and bracket designs across **material**, **cross-section**,
and **dimensions**, then recommends the best option under a chosen priority —
lightest, cheapest, highest factor of safety, or best-balanced — and visualizes
the tradeoffs.

> Status: scaffolded. Core library implemented to pass the test suite in `tests/`.
> See `SPEC.md` for the build contract.

## What it does

Given a load, span, load case, and a target factor of safety, MechOpt:

1. Computes stress, deflection, and factor of safety for every candidate design.
2. Filters to the designs that are actually safe (FoS ≥ target).
3. Picks winners: lightest safe, cheapest safe, highest FoS, and best-balanced.
4. Plots weight vs. cost vs. strength tradeoffs (Pareto view).
5. Prints a short, reasoned design recommendation.

## Engineering basis

| Quantity            | Equation                                   |
|---------------------|--------------------------------------------|
| Rectangle I         | b·h³ / 12                                   |
| Circle I            | π·d⁴ / 64                                   |
| Bending stress      | σ = M·c / I                                 |
| Cantilever, end load| M = P·L,  δ = P·L³ / (3·E·I)                 |
| Simply sup., center | M = P·L/4,  δ = P·L³ / (48·E·I)             |
| Factor of safety    | FoS = σ_yield / σ                           |
| Weight / cost       | A·L·ρ ,  weight × cost-per-kg               |

## Worked example

Steel A36, solid 30×30 mm square, span L = 0.8 m, P = 300 N end load (cantilever):

- I = 6.75×10⁻⁸ m⁴
- σ ≈ 53.3 MPa
- δ ≈ 3.79 mm
- FoS ≈ 4.69 (safe)

## Assumptions

Linear-elastic material, small-deflection (Euler–Bernoulli) theory, static point
load, prismatic beam. Material property values are **nominal** grade values, not
vendor datasheet figures; cost figures are rough and market-dependent.

## Limitations (not modeled)

Buckling, stress concentrations, fatigue, shear deflection, dynamic/impact
loading, and joint/weld effects. MechOpt is a first-pass screening tool, not a
substitute for detailed analysis or review by a qualified engineer.

## Run it

```bash
pip install -r requirements.txt
pytest -v            # run the test suite
streamlit run app.py # launch the web app
```

## Project layout

```
mechopt/
  mechopt/        core library (materials, sections, beam, optimizer)
  tests/          pytest known-answer + behavioral tests
  app.py          Streamlit UI
  SPEC.md         build contract / engineering spec
  .github/        CI (runs pytest on every push)
```
