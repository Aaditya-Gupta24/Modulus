# MechOpt — Project Specification

This document is the implementation contract for MechOpt. Tests in `tests/` are
the oracle. This spec explains the engineering and software architecture behind
them. An automated coding agent or human should be able to implement the full
app from this document alone.

---

## 1. Project Goal

MechOpt is a **Streamlit-based mechanical design screening dashboard** for
early-stage design decisions. It supports:

1. **Beam Optimizer** — sweep materials, cross-sections, and dimensions to find
   the best beam under a chosen priority.
2. **Bracket Analysis** — evaluate a simplified wall-mounted bracket with plate
   bending and bolt group checks.
3. **Compare Designs** — side-by-side comparison of top safe candidates.
4. **Assumptions / Limitations** — transparent documentation of what is and is
   not modeled.

**Scope:** first-pass static analysis for educational, portfolio, and
concept-screening use. This tool is **not** a substitute for certified
engineering design, detailed FEA, or review by a qualified engineer.

---

## 2. App Architecture

### Folder structure

```
mechopt/
  mechopt/
    __init__.py          package marker + version
    materials.py         material property database (data only)
    sections.py          cross-section geometry → SectionProps(A, I, c)
    beam.py              beam mechanics: moment, stress, deflection, FoS
    bracket.py           simplified bracket: plate bending + bolt group
    optimizer.py         design-space sweep + recommendation logic
  tests/
    test_sections.py     geometry known-answer tests
    test_beam.py         beam mechanics known-answer tests
    test_optimizer.py    optimizer behavioral tests
    test_bracket.py      bracket known-answer tests
    test_materials.py    material database integrity tests
  app.py                 Streamlit UI (tabs)
  SPEC.md                this file
  README.md              user-facing documentation
  requirements.txt       Python dependencies
  pytest.ini             pytest configuration
  .github/               CI workflow (runs pytest on push)
```

### Module responsibilities

| Module          | Purpose |
|-----------------|---------|
| `materials.py`  | Frozen dataclass `Material(name, E, sigma_y, rho, cost)` and the `MATERIALS` dict. Data only — no logic. |
| `sections.py`   | Pure functions returning `SectionProps(A, I, c)` for each cross-section type. Input validation raises `ValueError`. |
| `beam.py`       | `max_moment`, `max_stress`, `max_deflection`, `factor_of_safety`. Two load cases. |
| `bracket.py`    | `evaluate_bracket` → `BracketResult`. Plate bending + bolt group shear/tension. |
| `optimizer.py`  | `evaluate_candidates` → DataFrame, `recommend` → Series. Brute-force sweep. |
| `app.py`        | Streamlit UI only. Calls library functions; contains no engineering logic. |

---

## 3. UI Layout

`app.py` uses `st.tabs` with four tabs:

### Tab 1 — Beam Optimizer
- Inputs: load P, span L, load case, material selection, section type selection,
  target FoS, optional deflection limit, design priority.
- Outputs: recommended design metrics (material, section, dims, stress, deflection,
  FoS, weight, cost, pass/fail, controlling constraint), candidate table,
  tradeoff scatter plots.

### Tab 2 — Bracket Analysis
- Inputs: load P, offset e, plate width/thickness, material, target FoS,
  optional deflection limit, bolt count/diameter/spacing, bolt allowable stress.
- Outputs: plate stress, plate deflection, plate FoS, bolt shear/tension,
  bolt FoS, overall FoS, safe/unsafe, controlling failure mode, engineering
  interpretation text.

### Tab 3 — Compare Designs
- Top 5 safe beam designs by weight, cost, and FoS.
- Winners table (lightest, cheapest, safest, balanced).
- Bracket result summary.

### Tab 4 — Assumptions / Limitations
- Bullet list of all simplifications and exclusions.
- Warning: not a substitute for formal engineering review.

---

## 4. Materials

Each material is a frozen dataclass:

```python
@dataclass(frozen=True)
class Material:
    name: str
    E: float          # Young's modulus [Pa]
    sigma_y: float    # yield strength [Pa]
    rho: float        # density [kg/m³]
    cost: float       # approximate cost [USD/kg]
```

### Default materials

| Key                | Name               | E [Pa]  | σ_y [Pa] | ρ [kg/m³] | Cost [$/kg] |
|--------------------|--------------------|---------|----------|-----------|-------------|
| `aluminum_6061`    | Aluminum 6061-T6   | 69e9    | 275e6    | 2700      | 3.5         |
| `steel_a36`        | Steel A36          | 200e9   | 250e6    | 7850      | 1.0         |
| `pla`              | PLA (3D print)     | 3.5e9   | 50e6     | 1240      | 25.0        |
| `titanium_ti6al4v` | Titanium Ti-6Al-4V | 114e9   | 880e6    | 4430      | 35.0        |
| `brass_360`        | Brass C360         | 100e9   | 125e6    | 8500      | 6.0         |
| `abs_plastic`      | ABS (3D print)     | 2.3e9   | 40e6     | 1050      | 20.0        |

These are **nominal grade values**, not vendor datasheet figures. Cost values are
rough order-of-magnitude and market-dependent. Treat as relative, not absolute.

### Materials test

`test_materials.py` asserts:
- All six keys exist in `MATERIALS`.
- Every `Material` has positive `E`, `sigma_y`, `rho`, `cost`.

---

## 5. Cross-Section Geometry

All section functions live in `mechopt/sections.py` and return:

```python
@dataclass(frozen=True)
class SectionProps:
    A: float    # cross-sectional area [m²]
    I: float    # second moment of area [m⁴]
    c: float    # neutral axis to outer fibre [m]
```

### Section formulas

| Section            | A                                | I                                        | c   | Validation |
|--------------------|----------------------------------|------------------------------------------|-----|------------|
| `rectangle(b, h)`  | b·h                              | b·h³ / 12                                | h/2 | b, h > 0 |
| `circle(d)`        | π·d² / 4                         | π·d⁴ / 64                                | d/2 | d > 0 |
| `i_beam(b, h, tf, tw)` | b·h − (b−tw)·(h−2·tf)       | [b·h³ − (b−tw)·(h−2·tf)³] / 12          | h/2 | h > 2·tf, b > tw |
| `square_tube(a, w)` | a² − (a−2w)²                    | [a⁴ − (a−2w)⁴] / 12                     | a/2 | w > 0, 2w < a |
| `hollow_rectangle(b, h, w)` | b·h − (b−2w)·(h−2w)    | [b·h³ − (b−2w)·(h−2w)³] / 12            | h/2 | w > 0, 2w < min(b,h) |
| `hollow_circle(d, di)` | π·(d² − di²) / 4            | π·(d⁴ − di⁴) / 64                       | d/2 | 0 ≤ di < d |

Invalid geometry must raise `ValueError`.

### Known-answer section cases (hand-verified)

**Case A** — `rectangle(0.02, 0.02)`:
- A = 4.0e-4 m², I = 1.3333e-8 m⁴, c = 0.01 m

**Case B** — `circle(0.03)`:
- A = π·0.03²/4, I ≈ 3.97608e-8 m⁴, c = 0.015 m

**Case C** — `hollow_rectangle(0.040, 0.060, 0.004)`:
- A = 7.36000e-4 m², I = 3.450453e-7 m⁴, c = 0.030 m

**Case D** — `hollow_circle(0.050, 0.042)`:
- A = 5.780530e-4 m², I = 1.540511e-7 m⁴, c = 0.025 m

**Case E** — `square_tube(0.040, 0.004)`:
- A = 5.760000e-4 m², I = 1.259520e-7 m⁴, c = 0.020 m

### Degenerate / sanity tests

- `i_beam` with `tw = b` reduces to solid `rectangle` (void width → 0).
- `hollow_circle(d, 0)` equals `circle(d)`.
- `square_tube(a, a/2 − ε)` approaches `rectangle(a, a)`.
- `hollow_rectangle(b, h, min(b,h)/2 − ε)` approaches `rectangle(b, h)`.
- I-beam has higher I/A ratio than solid rectangle of same outer dims.

---

## 6. Beam Mechanics

Module: `mechopt/beam.py`. All functions are pure; no side effects.

### Load cases

| `load_case`      | Max moment M  | Max deflection δ       |
|------------------|---------------|------------------------|
| `cantilever_end` | P·L           | P·L³ / (3·E·I)        |
| `simply_center`  | P·L / 4       | P·L³ / (48·E·I)       |

Unknown load case strings must raise `ValueError`.

### Derived quantities

```
σ = M·c / I              bending stress [Pa]
FoS = σ_y / σ            factor of safety (against yield)
weight = A·L·ρ           beam mass [kg]
cost = weight · cost/kg   beam cost [USD]
```

### Known-answer beam cases

**Case A** — Steel A36, rectangle 30×30 mm, L = 0.8 m, P = 300 N, cantilever_end:
- M = 240.0 N·m
- I = 6.75e-8 m⁴
- σ ≈ 53.333 MPa
- δ ≈ 3.7926 mm
- FoS ≈ 4.6875

**Case B** — Aluminum 6061, circle d = 30 mm, L = 1.2 m, P = 800 N, simply_center:
- M = 240.0 N·m
- I ≈ 3.97608e-8 m⁴
- σ ≈ 90.541 MPa
- δ ≈ 10.4976 mm
- FoS ≈ 3.0373

**Basic FoS** — `factor_of_safety(100e6, 250e6)` = 2.5

---

## 7. Beam Optimizer

Module: `mechopt/optimizer.py`.

### `evaluate_candidates` contract

```python
def evaluate_candidates(
    load: float,
    length: float,
    load_case: str,
    fos_target: float,
    *,
    material_keys: list = None,      # default: all materials
    section_types: list = None,      # default: ["rectangle", "circle"]
    deflection_limit: float = None,  # default: no limit
) -> pd.DataFrame
```

Returns a DataFrame with **one row per candidate** and these **exact columns**:

```
material, section, dims, area, I, weight, cost, stress, deflection, fos, safe
```

- `dims`: human-readable string, e.g. `"30x30 mm"`, `"d=30 mm"`.
- `safe`: bool — `fos >= fos_target` **AND** `deflection <= deflection_limit`
  (if deflection_limit is set).

### Dimension sweep

Outer dimension `d` sweeps 10 to 100 mm in 10 mm steps (i.e. `[10, 20, ..., 100]`).

For each dimension, candidate sections are generated with sensible proportions:
- **rectangle**: square b = h = d.
- **circle**: diameter = d.
- **i_beam**: b = h = d, tf = tw = d/10 (skip if invalid geometry).
- **square_tube**: a = d, wall = max(d/10, 2 mm) (skip if 2w ≥ d).
- **hollow_rectangle**: b = h = d, wall = max(d/10, 2 mm) (skip if 2w ≥ d).
- **hollow_circle**: outer d, wall = max(d/10, 2 mm), di = d − 2·wall (skip if di ≤ 0).

### `recommend` contract

```python
def recommend(df: pd.DataFrame, priority: str = "balanced") -> pd.Series
```

From **safe rows only**, return one row:

| Priority    | Selection rule                                  |
|-------------|------------------------------------------------|
| `lightest`  | min `weight`                                    |
| `cheapest`  | min `cost`                                      |
| `safest`    | max `fos`                                       |
| `balanced`  | min of `weight_norm + cost_norm` (see below)    |

Balanced score:
```
weight_norm = (weight − min) / (max − min + 1e-12)
cost_norm   = (cost   − min) / (max − min + 1e-12)
score = weight_norm + cost_norm
```

Raise `ValueError` if no safe candidate exists.

### Controlling constraint (UI-level)

Determined in `app.py` (not in `optimizer.py`) using utilization ratios:
```
stress_utilization     = fos_target / fos
deflection_utilization = deflection / deflection_limit   (if limit set)
```
The constraint with the **highest utilization** controls.

---

## 8. Bracket Analysis

Module: `mechopt/bracket.py`.

### Model

A rectangular plate/arm cantilevered from a wall, loaded at offset `e` from the
wall, fastened with a vertical bolt group. This is a **simplified first-pass
model**.

### Data classes

```python
@dataclass(frozen=True)
class BoltResult:
    shear_per_bolt: float       # N
    max_tension: float          # N
    bolt_area: float            # m²
    shear_stress: float         # Pa
    tension_stress: float       # Pa
    combined_utilization: float # dimensionless (≤1 is OK)
    bolt_fos: float             # dimensionless

@dataclass(frozen=True)
class BracketResult:
    plate_stress: float         # Pa
    plate_deflection: float     # m
    plate_fos: float
    bolt: BoltResult
    overall_fos: float
    safe: bool
    controlling: str            # "plate_bending" | "bolt" | "deflection"
```

### `evaluate_bracket` contract

```python
def evaluate_bracket(
    P: float,                          # load [N]
    e: float,                          # load offset from wall [m]
    width: float,                      # plate width [m]
    thickness: float,                  # plate thickness [m]
    mat: Material,                     # plate material
    fos_target: float,                 # minimum FoS
    bolt_count: int,                   # number of bolts
    bolt_diameter: float,              # bolt shank diameter [m]
    bolt_spacing_v: float,             # vertical bolt spacing [m]
    bolt_sigma_allow: float = 640e6,   # bolt allowable stress [Pa]
    deflection_limit: float = None,    # max deflection [m] or None
) -> BracketResult
```

### Plate calculations

```
M = P · e                             bending moment [N·m]
I = width · thickness³ / 12           second moment of area [m⁴]
c = thickness / 2                     outer fibre distance [m]
σ_plate = M · c / I                   plate bending stress [Pa]
δ_plate = P · e³ / (3 · E · I)       tip deflection [m]
FoS_plate = σ_y / σ_plate            plate factor of safety
```

### Bolt group calculations

Bolt positions: vertical line of `n` bolts, equally spaced by `bolt_spacing_v`,
centred on the bolt-group centroid:

```
y_i = (i − (n−1)/2) · bolt_spacing_v     for i = 0, 1, ..., n−1
```

Direct shear (equally distributed):
```
V_per_bolt = P / n
```

Moment-induced tension (linear elastic distribution):
```
T_i = M · |y_i| / Σ(y_j²)
T_max = max(T_i)
```

Single-bolt fallback (n = 1, y = 0):
```
T_max = M / max(bolt_diameter, 1e-6)     conservative estimate
```

Bolt stresses:
```
A_bolt = π · d_bolt² / 4
τ_bolt = V_per_bolt / A_bolt
σ_bolt_tension = T_max / A_bolt
σ_combined = √(τ² + σ_tension²)
utilization = σ_combined / σ_allow
FoS_bolt = σ_allow / σ_combined
```

### Overall bracket result

```
FoS_overall = min(FoS_plate, FoS_bolt)
```

Controlling constraint:
1. If `deflection_limit` is set and `δ > deflection_limit` → `"deflection"`, `safe = False`.
2. Else if `FoS_plate < FoS_bolt` → `"plate_bending"`.
3. Else → `"bolt"`.
4. `safe = (FoS_overall ≥ fos_target)` AND deflection OK.

### Known-answer bracket cases

**Plate stress** — P = 500 N, e = 0.15 m, width = 0.08 m, thickness = 0.01 m:
- M = 75 N·m
- I = 6.6667e-9 m⁴
- σ = 56.25 MPa

**Bolt shear** — P = 500 N, 4 bolts:
- V_per_bolt = 125 N

**Overall FoS** — equals `min(plate_fos, bolt_fos)`.

**Deflection limit** — tight limit (1e-9 m) → `safe = False`,
`controlling = "deflection"`.

### Bracket UI

The bracket tab shows:
- Plate stress [MPa], deflection [mm], plate FoS.
- Bolt shear/bolt, max tension, bolt FoS, bolt utilization.
- Overall FoS, safe/unsafe status, controlling failure mode.
- Engineering interpretation: what controls the design and what change would
  help most (increase thickness, bolt diameter, bolt spacing, or reduce offset).

### Not modeled (bracket)

Welds, fatigue, stress concentrations at bolt holes, local tear-out, bearing
failure, prying action, plate buckling, detailed bolt preload/thread engagement,
FEA-level stress distribution.

---

## 9. Assumptions & Limitations (full list)

The Assumptions tab and README must document all of these:

### What is modeled
- Linear-elastic material behaviour (Hooke's law).
- Static point loads only.
- Small-deflection (Euler–Bernoulli) beam theory.
- Prismatic (constant cross-section) beams.
- Yielding-based factor of safety.
- Simplified cantilever plate model for brackets.
- Linear elastic bolt group load distribution.

### What is NOT modeled
- Buckling (lateral-torsional, local, plate).
- Stress concentrations (holes, notches, fillets).
- Fatigue or cyclic loading.
- Shear deflection (significant for short, deep beams).
- Dynamic or impact loads.
- Weld or joint design.
- Thermal effects.
- Combined loading (axial + bending + torsion).
- Corrosion / environmental degradation.
- Bearing, tear-out, block shear, or edge-distance checks.
- Prying action on bolts.
- Bolt preload / thread engagement.
- Detailed bolt pattern moment capacity (only simplified vertical line).

### Warning

> Do not use this tool as the sole basis for manufacturing or safety-critical
> design decisions. All results should be verified by a qualified engineer.

---

## 10. Testing Requirements

### Existing tests (do not modify)

| File                 | Tests |
|----------------------|-------|
| `test_sections.py`   | Known-answer for rectangle, circle, i_beam, hollow_rectangle, hollow_circle, square_tube + degenerate cases + invalid geometry. |
| `test_beam.py`       | Cases A and B (see §6) + basic FoS check. |
| `test_optimizer.py`  | DataFrame shape/columns, safe flag consistency, lightest/cheapest/safest match expected min/max, no-safe-design raises ValueError. |
| `test_materials.py`  | All 6 material keys exist; all properties positive. |
| `test_bracket.py`    | Plate props, plate stress (56.25 MPa), plate deflection, plate FoS, bolt shear (125 N for 4 bolts), overall FoS = min, deflection limit → unsafe, safe design check. |

### Test conventions

- Use `pytest.approx` with explicit `rel` tolerance (typically `1e-4`).
- Known-answer targets are hand-verified — do not weaken tolerances.
- Tests are the oracle; fix the implementation, not the tests.

---

## 11. Validation Rules

All modules should validate inputs at system boundaries:

| Input              | Rule                          | Error |
|--------------------|-------------------------------|-------|
| Load P             | > 0                           | `ValueError` |
| Span / offset      | > 0                           | `ValueError` |
| Dimensions         | > 0                           | `ValueError` |
| Wall thickness w   | > 0 and 2w < outer dimension  | `ValueError` |
| Inner diameter di  | 0 ≤ di < d                    | `ValueError` |
| I-beam tf, tw      | h > 2tf, b > tw               | `ValueError` |
| Load case string   | must be known                 | `ValueError` |
| Priority string    | must be known                 | `ValueError` |

In the Streamlit UI, use `st.error` for user-friendly messages rather than
letting exceptions propagate.

---

## 12. Streamlit UI Quality

### Widgets to use

`st.tabs`, `st.columns`, `st.metric`, `st.dataframe`, `st.expander`,
`st.scatter_chart`, `st.warning`, `st.success`, `st.error`, `st.info`,
`st.number_input`, `st.selectbox`, `st.multiselect`.

### Layout principles

- Advanced settings (material/section selection) go inside `st.expander`.
- First screen should not overwhelm — show inputs and recommendation first.
- Candidate table and plots below the fold.
- Use metrics for key numbers (FoS, stress, deflection, weight, cost).
- Color-code safe (green) / unsafe (red) in tables.
- No emojis in engineering output except ✓ / ✗ for pass/fail.

---

## 13. Implementation Priority

1. SPEC.md (this file) — clear and complete.
2. Refactor `app.py` into tabs without breaking existing beam functionality.
3. Add deflection limit and controlling constraint to beam optimizer.
4. Implement `mechopt/bracket.py` with plate + bolt group calculations.
5. Add `tests/test_bracket.py`.
6. Add Bracket Analysis tab to `app.py`.
7. Add Compare Designs tab.
8. Add Assumptions / Limitations tab.
9. Polish layout and explanatory text.
10. Update `README.md`.

---

## 14. Acceptance Criteria

The project is **done** when:

1. `pytest` is green (all tests pass).
2. CI passes on GitHub.
3. `app.py` runs and shows all four tabs.
4. Beam optimizer still works with material/section filtering and deflection limits.
5. Bracket Analysis tab evaluates plate bending + bolt group and shows
   controlling failure mode.
6. Compare Designs tab shows top-5 tables and winners.
7. Assumptions tab clearly documents all limitations.
8. README documents assumptions, equations, worked examples, and limitations.
9. The app is technically credible but remains simple enough for a student
   portfolio project.

---

## 15. Units

All internal calculations use **SI base units**:

| Quantity     | Unit   |
|-------------|--------|
| Length       | m      |
| Force        | N      |
| Stress       | Pa     |
| Area         | m²     |
| Moment of I  | m⁴     |
| Density      | kg/m³  |
| Mass         | kg     |
| Cost         | USD    |

The UI converts for display: stress → MPa, deflection → mm.
