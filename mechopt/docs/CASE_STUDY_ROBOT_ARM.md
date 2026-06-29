# Case Study — Stiffness controls before stress in a robot-arm link

"Strong enough" and "stiff enough" are different requirements. This case
demonstrates how a tight deflection limit eliminates many high-FoS candidates
before stress ever becomes the binding constraint.

## The problem

A robot arm link made from **Aluminum 6061-T6**, simply supported at both ends
with a center load. The geometry is compact — short span, modest load — exactly
the regime where engineers expect stress to be the easy constraint. It is not.

| Parameter | Value |
|---|---|
| Material | Aluminum 6061-T6 |
| Span | L = 0.5 m |
| Center load | P = 200 N |
| Load case | Simply supported, center point load |
| Required FoS | ≥ 2.0 |
| Deflection limit | δ ≤ 0.5 mm |
| Sections swept | rectangle, circle, hollow_circle, square_tube |

Material constants: E = 69 GPa, σ_y = 275 MPa, ρ = 2700 kg/m³.

Governing equations (Euler-Bernoulli, simply supported center load):

```
M_max = P·L / 4
σ_max = M_max · c / I
δ_max = P·L³ / (48·E·I)
FoS   = σ_y / σ_max
```

## The result

MechOpt sweeps 20 mm, 30 mm, 40 mm, 50 mm sizes across all four section
families and evaluates both constraints. The table below shows representative
candidates in ascending order of section size. **PASS/FAIL applies to the
deflection check; every candidate shown already meets FoS ≥ 2.0.**

| Section | Size | I (m⁴) | σ (MPa) | FoS | δ (mm) | Deflection check |
|---|---|---|---|---|---|---|
| rectangle | 20 × 20 mm | 1.333 × 10⁻⁸ | 18.75 | **14.67** | **0.566** | FAIL |
| circle | d = 25 mm | 1.917 × 10⁻⁸ | 16.38 | **16.79** | **0.394** | FAIL |
| rectangle | 30 × 30 mm | 6.750 × 10⁻⁸ | 8.33 | **33.0** | **0.112** | PASS |
| hollow_circle | d = 30, dᵢ = 24 mm | 2.338 × 10⁻⁸ | 12.82 | 21.45 | **0.325** | FAIL |
| hollow_circle | d = 40, dᵢ = 32 mm | 7.540 × 10⁻⁸ | 6.63 | 41.5 | **0.101** | PASS |
| square_tube | 30 mm, w = 3 mm | 3.510 × 10⁻⁸ | 10.68 | 25.8 | **0.216** | FAIL |
| square_tube | 40 mm, w = 4 mm | 1.260 × 10⁻⁷ | 3.97 | 69.2 | **0.060** | PASS |

Derived values for the two instructive extremes:

**Rectangle 20 × 20 mm** (high FoS, fails deflection):

```
I = (0.02)⁴ / 12 = 1.333 × 10⁻⁸ m⁴
M = 200 × 0.5 / 4 = 25 N·m
σ = 25 × 0.010 / 1.333×10⁻⁸ = 18.75 MPa
FoS = 275 / 18.75 = 14.67                      ← far above target
δ = 200 × (0.5)³ / (48 × 69×10⁹ × 1.333×10⁻⁸)
  = 25 / 44,148 = 5.66 × 10⁻⁴ m = 0.566 mm    ← exceeds 0.5 mm limit
```

This section is **14.7× stronger than required and yet fails the design check.**

**Rectangle 30 × 30 mm** (first passing candidate in this family):

```
I = (0.03)⁴ / 12 = 6.750 × 10⁻⁸ m⁴
δ = 200 × (0.5)³ / (48 × 69×10⁹ × 6.750×10⁻⁸)
  = 25 / 223,560 = 1.12 × 10⁻⁴ m = 0.112 mm   ← comfortably within limit
```

Tripling the cross-sectional area (from 400 mm² to 900 mm²) reduces deflection
by 80 %, from 0.566 mm to 0.112 mm. Stress was already irrelevant at 20 mm;
stiffness is what forced the upsize.

## The winner

The **square_tube 40 × 40 mm, wall 4 mm** is the lightest passing candidate that
satisfies both constraints:

```
A = 40² − 32² = 576 mm² = 5.76 × 10⁻⁴ m²
I = (40⁴ − 32⁴) / 12 mm⁴ = (2,560,000 − 1,048,576) / 12 = 125,952 mm⁴
  = 1.260 × 10⁻⁷ m⁴
mass = A · L · ρ = 5.76×10⁻⁴ × 0.5 × 2700 = 0.778 kg

δ = 200 × (0.5)³ / (48 × 69×10⁹ × 1.260×10⁻⁷)
  = 25 / 417,744 = 5.99 × 10⁻⁵ m = 0.060 mm
```

Deflection is 0.060 mm — 88 % below the 0.5 mm limit — and mass is 0.778 kg.
The hollow section wins because removing the low-efficiency material near the
neutral axis and pushing area toward the outer walls raises I without adding
proportional mass. A solid 40 mm square has I = 8.53 × 10⁻⁸ m⁴ and mass
1.728 kg; the tube achieves 1.48× higher I at 45 % of the mass.

## Why — the engineering reason

Deflection and stress scale differently with geometry. Stress is `σ = M·c/I`;
deflection is `δ = P·L³/(48EI)`. Both have I in the denominator, but the
critical difference is how quickly I grows as the section scales up.

For a solid rectangle of side h, `I = h⁴/12`. Double the side length and I
grows by 16×. Stress drops by the same factor — but so does deflection. The
ratio between the two constraints does not shift: if deflection controls at
h = 20 mm, it still controls at h = 30 mm. The only way to escape deflection
dominance is to choose a stiffer material (higher E) or switch to a section
geometry that buys more I per unit mass — namely a tube or I-beam.

In this problem, E = 69 GPa (aluminum) and L = 0.5 m. The stiffness
denominator `48EI` grows slowly for compact solid sections, so a compact section
must be oversized for strength before it is stiff enough. That is the source of
the FoS = 14.67 / deflection-fail paradox. The 20 mm rectangle is sitting at
the intersection of "strong enough" and "not nearly stiff enough."

This pattern shows up wherever precision matters: robotic joints, optical mounts,
machine tool spindles, any structure where a positional error budget is tighter
than a failure-load budget. Standard structural design focuses on avoiding
fracture; mechatronic design often focuses on avoiding motion error instead.

## What a real engineer would add

This analysis covers static, linear-elastic bending at a single operating load.
For an actual robot arm, the following effects are **not modeled here** and may
control the final design:

- **Natural frequency / resonance.** A robot arm is a dynamic system. The first
  natural frequency `f₁ ∝ √(EI/mL³)` must stay above the excitation frequencies
  from servo motion. A stiffer section raises f₁; the deflection limit already
  pushes in the same direction, but the required frequency may be more stringent
  than the static deflection limit implies.
- **Fatigue from cyclic motion.** Each repetition cycle is a load cycle. Aluminum
  6061-T6 has a fatigue limit around 96 MPa (R = −1 fully reversed); at
  σ = 18.75 MPa the static FoS looks huge, but cyclic FoS depends on the S-N
  curve, stress concentration at joints, and surface finish. The stress
  concentration at pin holes or welds will dominate.
- **Joint stiffness.** The end supports here are modeled as ideal pins. Real
  robot joints have finite rotational stiffness from bearings, flexures, or
  compliant couplings. Joint compliance can contribute as much tip deflection
  as the link itself for short, stiff links.
- **Inertial loading.** Acceleration of the arm during motion creates distributed
  inertia loads along the link length that are absent from the static model.
- **Anisotropy and extrusion direction.** Aluminum 6061-T6 properties differ
  slightly along and transverse to the extrusion axis. For rolled bar stock, the
  values above are conservative in the extrusion direction.

MechOpt's role here is screening: it found, from first principles, that this
configuration is stiffness-dominated and that hollow sections are the right
family to pursue. The next step is a detailed finite-element model of the
candidate link with the real joint and load conditions.

_Reproduce: in the Beam Optimizer tab, set material = Aluminum 6061, load case =
simply supported center, L = 0.5 m, P = 200 N, FoS target = 2.0, deflection
limit = 0.5 mm, priority = lightest. The ranked table will show the deflection
failures alongside high-FoS values._
