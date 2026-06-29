---
name: mechanical-engineering-mentor
description: Structural mechanics equations and oracle-derivation methodology for MechOpt. Trigger when hand-deriving beam, bracket, buckling, or failure-mode targets.
---

# Mechanical Engineering Mentor

You have deep expertise in structural mechanics at the undergraduate ME level. Use this knowledge when deriving oracle targets for MechOpt.

## Core equations (MechOpt scope)

### Sections
- Rectangle: A = bh, I = bh³/12, c = h/2
- Circle: A = πd²/4, I = πd⁴/64, c = d/2
- Hollow rectangle: b_i = b−2w, h_i = h−2w, A = bh − b_i·h_i, I = (bh³ − b_i·h_i³)/12, c = h/2
- Hollow circle: A = π(d² − d_i²)/4, I = π(d⁴ − d_i⁴)/64, c = d/2
- Square tube: a_i = a−2w, A = a² − a_i², I = (a⁴ − a_i⁴)/12, c = a/2
- I-beam: A = bh − (b−t_w)(h−2t_f), I = (bh³ − (b−t_w)(h−2t_f)³)/12, c = h/2

### Beams
- Cantilever end load: M = PL, δ = PL³/(3EI)
- Simply supported center load: M = PL/4, δ = PL³/(48EI)
- Bending stress: σ = Mc/I
- Factor of safety: FoS = σ_y / σ
- Weight: A·L·ρ
- Cost: weight × cost_per_kg

### Bracket
- Plate bending: M = P·e, σ_b = Mc/I (plate as cantilever)
- Bolt direct shear: V = P/n
- Bolt moment tension: T_i = M·r_i / Δr²
- Combined bolt: σ_vm = √(τ² + σ²)
- Overall FoS = min(plate_FoS, bolt_FoS)

### Buckling
- Euler critical load: P_cr = π²EI / (KL)²
- Radius of gyration: r = √(I/A)
- Slenderness ratio: λ = KL/r

### Failure modes (Milestone A)
- CheckResult: (name, actual, allowable, margin, status, notes)
- Margin = (allowable − actual) / allowable (for stress-like) or actual/allowable (for FoS-like)
- Status: pass | fail | warning | not_modeled
- Shear and torsion are declared not_modeled (honest warning)

## Oracle derivation methodology
1. State the governing equation
2. Substitute known values with units
3. Show every arithmetic step
4. Never round intermediate values
5. Final answer matches precision of inputs
6. Cross-check against PROJECT_CONTEXT §7 verified numbers
7. If derivation contradicts a verified number, STOP and flag

## Golden rule
**Fix the code, never edit a verified test target.**
