# MechOpt — Build Spec

This file is the contract for the implementation. An automated coding loop (or a
human) should make all tests in `tests/` pass **without changing the test files
or any function signatures**. The tests are the oracle; this document explains
the engineering behind them.

## Goal

A tool that, given a load and span, screens beam/bracket designs across material,
cross-section, and dimension, and recommends the best one under a chosen
priority (lightest / cheapest / safest / balanced), with tradeoff plots.

## Scope & assumptions (intentional simplifications)

- Linear-elastic material, small-deflection (Euler–Bernoulli) beam theory.
- Static point load. Two load cases only (below).
- Prismatic (constant cross-section) beam.
- Failure criterion = yielding. **Not modeled:** buckling, stress
  concentrations, fatigue, shear deflection, dynamic/impact loads, weld/joint
  effects. These are listed as limitations in the README on purpose.

## Equations

Second moment of area `I` and outer-fibre distance `c`:

| Section    | A                         | I                                              | c   |
|------------|---------------------------|------------------------------------------------|-----|
| rectangle  | b·h                       | b·h³ / 12                                       | h/2 |
| circle     | π·d²/4                    | π·d⁴ / 64                                       | d/2 |
| I-beam     | b·h − (b−tw)(h−2·tf)      | [b·h³ − (b−tw)(h−2·tf)³] / 12                   | h/2 |

Load cases:

| load_case        | max moment M | max deflection δ        |
|------------------|--------------|-------------------------|
| cantilever_end   | P·L          | P·L³ / (3·E·I)          |
| simply_center    | P·L / 4      | P·L³ / (48·E·I)         |

Then: `σ = M·c / I`, `FoS = σ_y / σ`, `weight = A·L·ρ`, `cost = weight · cost_per_kg`.

## Modules to implement

- `mechopt/sections.py` — `rectangle`, `circle`, `i_beam` → `SectionProps(A, I, c)`.
- `mechopt/beam.py` — `max_moment`, `max_stress`, `max_deflection`, `factor_of_safety`.
- `mechopt/optimizer.py` — `evaluate_candidates`, `recommend`.
- `app.py` — Streamlit UI (build last, after the library is green).

`mechopt/materials.py` is already provided (data only).

## evaluate_candidates contract

Returns a pandas DataFrame, one row per candidate, with **exact** columns:
`material, section, dims, area, I, weight, cost, stress, deflection, fos, safe`.
`safe` is `fos >= fos_target`. Sweep at least the three materials, the
rectangle and circle sections, and a reasonable range of dimensions.

## recommend contract

From the SAFE rows only, return one row:
`lightest`→min weight, `cheapest`→min cost, `safest`→max fos,
`balanced`→min of normalized (weight + cost). Raise `ValueError` if nothing is safe.

## Known-answer reference cases (these are what the tests check)

Case A — steel A36, solid square 30×30 mm, L = 0.8 m, P = 300 N, cantilever_end:
- I = 6.75e-8 m⁴
- σ ≈ 53.333 MPa
- δ ≈ 3.7926 mm
- FoS ≈ 4.6875

Case B — aluminum 6061, solid circle d = 30 mm, L = 1.2 m, P = 800 N, simply_center:
- I ≈ 3.97608e-8 m⁴
- σ ≈ 90.541 MPa
- δ ≈ 10.4976 mm
- FoS ≈ 3.0373

Verify these by hand before trusting any implementation.

## Definition of done

1. `pytest` is green.
2. CI passes on GitHub.
3. `app.py` runs and reproduces a recommendation.
4. README documents assumptions, equations, a worked example, results, limitations.
