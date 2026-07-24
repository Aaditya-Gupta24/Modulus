# Case Study — Buckling controls a crane compression strut before yielding does

A compression member that looks safe by yield stress can buckle catastrophically
at a fraction of its yield load. This case shows how a small solid section can
carry a compressive axial stress of 5 MPa — giving a yield FoS of 50 — and still
fail the Euler buckling check with a buckling FoS of 1.46.

## The problem

A vertical compression strut in a small portable crane or hoist. The strut is
fixed at the base and free at the top (cantilever end condition, K = 2.0), which
is the worst-case buckling boundary condition for a column. Load is purely axial
compression from the lifted load.

| Parameter | Value |
|---|---|
| Material | Steel A36 |
| Strut length | L = 1.5 m |
| Compressive load | P = 2000 N |
| Boundary condition | Fixed-free (cantilever), K = 2.0 |
| Required FoS | ≥ 2.0 (applied to buckling and yield) |
| Sections swept | rectangle, circle, hollow_circle, square_tube |

Material constants: E = 200 GPa, σ_y = 250 MPa, ρ = 7850 kg/m³.

Governing equations:

```
Euler critical load:   P_cr = π²·E·I / (K·L)²
Buckling FoS:          FoS_b = P_cr / P
Yield stress:          σ = P / A       (pure axial compression)
Yield FoS:             FoS_y = σ_y / σ
```

The effective length `(K·L)² = (2.0 × 1.5)² = 9.0 m²` appears in the
denominator. This is the key term: doubling K multiplies the effective length
squared by four, reducing P_cr by 4×.

## The result

The table below shows the two competing failure modes side by side. **A section
"passes" only when both FoS_b ≥ 2.0 and FoS_y ≥ 2.0.**

| Section | Size | A (mm²) | I (m⁴) | σ (MPa) | FoS_yield | P_cr (N) | FoS_buckling | Overall |
|---|---|---|---|---|---|---|---|---|
| rectangle | 20 × 20 mm | 400 | 1.333 × 10⁻⁸ | 5.00 | **50.0** | 2,921 | **1.46** | FAIL |
| rectangle | 30 × 30 mm | 900 | 6.750 × 10⁻⁸ | 2.22 | 112.5 | 14,804 | **7.40** | PASS |
| circle | d = 25 mm | 491 | 1.917 × 10⁻⁸ | 4.07 | **61.4** | 4,199 | **2.10** | PASS |
| circle | d = 20 mm | 314 | 7.854 × 10⁻⁹ | 6.37 | **39.2** | 1,720 | **0.86** | FAIL |
| hollow_circle | d = 30, dᵢ = 24 mm | 254 | 2.338 × 10⁻⁸ | 7.87 | **31.8** | 5,122 | **2.56** | PASS |
| square_tube | 40 mm, w = 4 mm | 576 | 1.260 × 10⁻⁷ | 3.47 | **72.0** | 27,600 | **13.8** | PASS |

Derived values for the two instructive extremes:

**Rectangle 20 × 20 mm** (yield looks safe, buckling fails):

```
A = 0.02 × 0.02 = 4 × 10⁻⁴ m²
I = (0.02)⁴ / 12 = 1.333 × 10⁻⁸ m⁴

Yield:
  σ = P / A = 2000 / 4×10⁻⁴ = 5.0 MPa
  FoS_yield = 250 / 5.0 = 50.0             ← looks extremely safe

Buckling:
  P_cr = π² × 200×10⁹ × 1.333×10⁻⁸ / 9.0
       = 9.8696 × 2666.0 / 9.0
       = 26,305 / 9.0 = 2,922 N
  FoS_b = 2922 / 2000 = 1.46               ← below the 2.0 target
```

The yield FoS is 34× higher than needed. The buckling FoS fails by 27 %.

**Square tube 40 × 40 mm, wall 4 mm** (recommended design):

```
I_outer = (0.04)⁴ / 12 = 2.133 × 10⁻⁷ m⁴
I_inner = (0.032)⁴ / 12 = 8.738 × 10⁻⁸ m⁴
I_tube  = 2.133×10⁻⁷ − 8.738×10⁻⁸ = 1.260 × 10⁻⁷ m⁴

A = (0.04)² − (0.032)² = 1.600×10⁻³ − 1.024×10⁻³ = 5.76 × 10⁻⁴ m²

P_cr = π² × 200×10⁹ × 1.260×10⁻⁷ / 9.0
     = 9.8696 × 25,200 / 9.0
     = 248,713 / 9.0 = 27,635 N
FoS_b = 27,635 / 2000 = 13.8

mass = A × L × ρ = 5.76×10⁻⁴ × 1.5 × 7850 = 6.79 kg
```

The tube section carries 9.5× the Euler critical load of the 20 mm solid bar at
less than 1.5× the mass (6.79 kg vs 4.71 kg for a 20 mm solid bar of the same
length). The difference is entirely in I: the tube's I is 9.5× larger because
it moves material to the outer walls where it contributes `y²` to the integral.

## Why — the engineering reason

Euler buckling is controlled by stiffness, not strength. The critical load
`P_cr = π²EI/(KL)²` contains E (material stiffness) and I (geometric stiffness)
but not σ_y. A material's yield strength is irrelevant to the buckling load. A
solid 20 mm aluminum bar and a solid 20 mm steel bar with identical geometry
buckle at loads proportional only to their E values (69 GPa vs 200 GPa), not to
their σ_y values.

This matters because solid sections are inefficient at resisting buckling. For a
solid square of side h, `I = h⁴/12` and `A = h²`, giving a radius of gyration
`r = √(I/A) = h/√12 ≈ 0.289h`. The slenderness ratio `λ = KL/r = 2×1.5/(0.289×h)`.
For h = 20 mm, λ = 3.0/(0.289×0.02) = 519 — a very slender column. Euler's
formula applies, and the section buckles long before the material yields.

Hollow sections dramatically increase r at a fraction of the mass penalty. The
square tube (40 mm outer, 4 mm wall) has:

```
r = √(I/A) = √(1.260×10⁻⁷ / 5.76×10⁻⁴) = √(2.188×10⁻⁴) = 0.01479 m = 14.79 mm
λ = KL / r = 3.0 / 0.01479 = 203
```

Versus the 20 mm solid bar:

```
r = 0.02 / √12 = 5.77 mm
λ = 3.0 / 0.00577 = 520
```

The tube reduces slenderness by 61 %. Since P_cr scales as 1/λ², that 61 %
reduction in λ produces (520/203)² = 6.55× more critical load. Hollow sections
are not just marginally better for compression members — they are categorically
better for the same reason they are better in bending: I per unit mass is far
higher.

Buckling failure is sudden and offers no warning. Yielding in bending or tension
produces visible deformation before fracture. Buckling, especially for slender
members in the Euler regime, produces a rapid, elastic snap to a deflected
equilibrium. The load capacity drops to near zero at the instant of buckling.
There is no safe working range between "buckling FoS = 1.0" and "failure." This
is why FoS targets for buckling are often set higher than for yielding in
practice — but the 2.0 target here already filters the 20 mm solid bars out
correctly.

## What a real engineer would add

This analysis uses the classical Euler formula, which applies to long, slender
columns in the elastic range. Several important effects are absent:

- **Inelastic buckling for intermediate slenderness.** When `λ = KL/r` falls
  below a material-dependent transition (roughly λ < 120 for A36 steel), the
  column is in the inelastic or tangent-modulus regime, and Euler overestimates
  P_cr. The Johnson parabola or AISC column curves reduce the allowable load. For
  the sections that pass here with low slenderness, this could lower the computed
  FoS by 15–30 %. The optimizer does not apply the Johnson correction; inspect
  the slenderness of the chosen section before finalizing.
- **Eccentric loading.** The model assumes the load is applied exactly on the
  centroidal axis. In a real crane, the hook, shackle, and fitting introduce
  eccentricity. Even a few millimeters of offset adds a bending moment that
  reduces effective P_cr via the secant formula. Eccentricity is not modeled.
- **Initial imperfections.** Real columns are never perfectly straight.
  Manufacturing tolerances and assembly misalignment add a geometric imperfection
  that reduces buckling load compared to the ideal Euler value. Codes account for
  this with additional reduction factors.
- **Dynamic and impact loads.** A crane drops loads, hits end stops, and
  experiences shock. A static P = 2000 N under dynamic amplification may become
  3000–4000 N instantaneously. The FoS target of 2.0 partially covers this, but
  the load case should be confirmed against the intended duty cycle.
- **Local wall buckling.** Square tubes can fail by local buckling of the walls
  before the global Euler mode triggers. The wall slenderness `b/t = 32/4 = 8`
  for the recommended section is well below typical plate-buckling limits, so
  global Euler governs here — but this should be verified for thinner-wall
  variants.
- **Connection details.** The fixed-free (K = 2.0) boundary condition requires a
  genuinely rigid base connection. A bolted base plate with some rotational
  compliance moves K toward 1.0–2.0; if the base rotates, the effective K can
  exceed 2.0, worsening the buckling load. The base connection design must match
  the assumed boundary condition.

Modulus identified the failure mode, ranked sections by buckling FoS, and showed
why hollow sections dominate. The next step for this strut is applying the AISC
column curve to the intermediate-slenderness candidates and checking the base
plate connection for rotational stiffness.

_Reproduce: in the Beam Optimizer tab, select material = Steel A36 and run with
load case = cantilever end, L = 1.5 m, P = 2000 N, FoS target = 2.0. The
failure-mode table will show the Euler buckling check alongside yield stress for
each candidate. For the 20 mm solid sections, buckling status is FAIL even while
the stress check shows PASS with large margin._
