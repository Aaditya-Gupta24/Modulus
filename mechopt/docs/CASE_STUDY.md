# Case Study — Why the optimizer prefers tubes and I-beams

A factor-of-safety number on its own doesn't justify a design. This walkthrough
uses MechOpt to make an actual decision and shows *why* the answer is what it is.

## The problem

Cantilever bracket arm, steel A36, span **L = 1.0 m**, end load **P = 600 N**,
required **factor of safety ≥ 2.0**. Which cross-section carries this load with the
least mass? MechOpt sweeps six section families across dimensions from 10–100 mm
and keeps the 41 safe candidates (of 60 total).

## The result

| Best in family | Section | FoS | Mass |
|----------------|---------|----:|-----:|
| Lightest **solid** | circle, d = 40 mm | 2.62 | **9.87 kg** |
| Lightest **hollow / I** | I-beam, 40×40, t = 4 mm | 2.40 | **3.52 kg** |

At essentially the same safety margin, the I-section does the same job for
**64 % less mass** (3.52 kg vs 9.87 kg). Across the whole sweep, the hollow/I
family forms the lower edge of the mass-vs-safety cloud — for any safety level you
choose, the lightest way to get there is a hollow section.

![Mass vs factor of safety](pareto.png)

## Why — the engineering reason

Bending stress is `σ = M·c / I`, so resistance to bending is governed by the
**second moment of area I**, and `I = ∫ y² dA`. The `y²` weighting means material
far from the neutral axis contributes far more stiffness per kilogram than
material near it. A solid bar wastes mass in the middle, where `y ≈ 0` and the
material barely resists bending. A tube or I-beam removes that low-value core and
pushes the same mass outward to large `y`, buying a much larger `I` for the same
weight.

That is the entire reason aircraft spars, bike frames, and scaffolding are
hollow — and MechOpt rediscovers it from first principles rather than being told.

## The caveat a real engineer would add

This screen ranks on bending strength only. Thin-walled tubes that win here can
**lose to local buckling** (wall crippling) that the model does not yet check — so
the I-beam's 64 % saving is an upper bound until a buckling check is added
(tracked on the roadmap). MechOpt is a screening tool: it narrows six families to
one or two worth analyzing properly, not the final word.

_Reproduce: `PYTHONPATH=. python -c "from mechopt.optimizer import evaluate_candidates; ..."`
or open the Beam Optimizer tab with these inputs._
